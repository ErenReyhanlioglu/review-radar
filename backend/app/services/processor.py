import asyncio
import logging
from typing import Any

from anthropic import AsyncAnthropic

from app.config import settings

logger = logging.getLogger(__name__)

TOPICS = [
    "veri kalitesi",
    "fiyat",
    "email deliverability",
    "UX / kullanım kolaylığı",
    "müşteri desteği",
    "entegrasyon",
    "arama & filtreleme",
    "otomasyon",
    "raporlama & analitik",
    "genel olumlu",
]

_TAG_TOOL = {
    "name": "tag_review",
    "description": "Apollo.io review analizini döndür.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "items": {"type": "string", "enum": TOPICS},
                "description": "İlgili konu etiketleri (birden fazla olabilir).",
            },
            "sentiment": {
                "type": "string",
                "enum": ["pozitif", "negatif", "nötr"],
                "description": "Genel duygu tonu.",
            },
            "summary": {
                "type": "string",
                "description": "1 cümlelik Türkçe özet.",
            },
        },
        "required": ["topics", "sentiment", "summary"],
    },
}

_SYSTEM = (
    "Apollo.io kullanıcı review'larını analiz ediyorsun. "
    "Her review için: konu etiketleri (listeden seç, birden fazla olabilir), "
    "duygu tonu ve 1 cümlelik Türkçe özet üret. "
    f"Konu listesi: {', '.join(TOPICS)}"
)

_POLL_INTERVAL = 10   # saniye
_MAX_WAIT = 1800      # 30 dakika timeout


def _build_request(review: dict) -> dict:
    likes = review.get("likes") or ""
    dislikes = review.get("dislikes") or ""
    text = f"Likes: {likes}\n\nDislikes: {dislikes}".strip()
    return {
        "custom_id": review["reviewId"],
        "params": {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "system": _SYSTEM,
            "tools": [_TAG_TOOL],
            "tool_choice": {"type": "tool", "name": "tag_review"},
            "messages": [{"role": "user", "content": text}],
        },
    }


async def enrich_reviews(reviews: list[dict]) -> dict[str, dict[str, Any]]:
    """
    Sends all reviews to Claude Batch API.
    Returns {review_id: {topics, sentiment, summary}} for successful results.
    Falls back to empty tags on individual failures.
    """
    if not reviews:
        return {}

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    requests = [_build_request(r) for r in reviews]

    logger.info("Batch oluşturuluyor: %d review", len(requests))
    batch = await client.messages.batches.create(requests=requests)
    batch_id = batch.id
    logger.info("Batch ID: %s — bekleniyor...", batch_id)

    elapsed = 0
    while elapsed < _MAX_WAIT:
        await asyncio.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL
        batch = await client.messages.batches.retrieve(batch_id)
        logger.info("Batch durumu: %s (%ds geçti)", batch.processing_status, elapsed)
        if batch.processing_status == "ended":
            break
    else:
        raise TimeoutError(f"Batch {batch_id} {_MAX_WAIT}s içinde tamamlanmadı.")

    results: dict[str, dict[str, Any]] = {}
    async for result in await client.messages.batches.results(batch_id):
        rid = result.custom_id
        if result.result.type != "succeeded":
            logger.warning("Batch sonucu başarısız: %s — %s", rid, result.result.type)
            results[rid] = {"topics": ["genel olumlu"], "sentiment": "nötr", "summary": ""}
            continue
        content = result.result.message.content
        tool_block = next((b for b in content if b.type == "tool_use"), None)
        if tool_block is None:
            logger.warning("tool_use bloğu yok: %s", rid)
            results[rid] = {"topics": ["genel olumlu"], "sentiment": "nötr", "summary": ""}
            continue
        results[rid] = tool_block.input

    return results
