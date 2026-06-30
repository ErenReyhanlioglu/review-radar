import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_MODEL = "text-embedding-3-small"
_BATCH_SIZE = 512  # OpenAI max 2048, 512 güvenli


def _build_text(review: dict) -> str:
    likes = review.get("likes") or ""
    dislikes = review.get("dislikes") or ""
    return f"What users like: {likes}\n\nWhat users dislike: {dislikes}"


async def embed_text(text: str) -> list[float]:
    """Embeds a single text string. Used by chat service for query vectors."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(model=_MODEL, input=[text])
    return response.data[0].embedding


async def embed_reviews(reviews: list[dict]) -> dict[str, list[float]]:
    """
    Returns {review_id: vector[1536]} for all reviews.
    Sends in batches of _BATCH_SIZE to stay within API limits.
    """
    if not reviews:
        return {}

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    results: dict[str, list[float]] = {}

    for i in range(0, len(reviews), _BATCH_SIZE):
        chunk = reviews[i : i + _BATCH_SIZE]
        texts = [_build_text(r) for r in chunk]
        ids = [r["reviewId"] for r in chunk]

        logger.info("Embedding: %d–%d / %d", i, i + len(chunk), len(reviews))
        response = await client.embeddings.create(model=_MODEL, input=texts)

        for review_id, embedding_obj in zip(ids, response.data):
            results[review_id] = embedding_obj.embedding

    return results
