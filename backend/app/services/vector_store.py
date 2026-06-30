import logging
import uuid
from datetime import date, datetime, time

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from app.config import settings

logger = logging.getLogger(__name__)

VECTOR_SIZE = 1536

_client: AsyncQdrantClient | None = None


def _get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=settings.qdrant_url)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def ensure_collection() -> None:
    client = _get_client()
    collections = await client.get_collections()
    names = [c.name for c in collections.collections]
    if settings.qdrant_collection not in names:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Collection oluşturuldu: %s", settings.qdrant_collection)


async def upsert_reviews(
    reviews: list[dict],
    enrichments: dict[str, dict],
    embeddings: dict[str, list[float]],
) -> None:
    """Upserts processed reviews into Qdrant."""
    client = _get_client()
    points = []

    for r in reviews:
        rid = r["reviewId"]
        vector = embeddings.get(rid)
        if vector is None:
            logger.warning("Embedding eksik, atlanıyor: %s", rid)
            continue

        enr = enrichments.get(rid, {})
        likes = r.get("likes") or ""
        dislikes = r.get("dislikes") or ""

        date_str = r.get("date")
        date_ts: float | None = None
        if date_str:
            try:
                date_ts = datetime.fromisoformat(date_str).timestamp()
            except ValueError:
                pass

        points.append(
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, rid)),
                vector=vector,
                payload={
                    "text": f"What users like: {likes}\n\nWhat users dislike: {dislikes}",
                    "review_id": rid,
                    "date": date_str,
                    "date_ts": date_ts,
                    "rating": r.get("starRating"),
                    "company_size": r.get("company_size") or "bilinmiyor",
                    "topics": enr.get("topics", []),
                    "sentiment": enr.get("sentiment", "nötr"),
                    "summary": enr.get("summary", ""),
                },
            )
        )

    if points:
        await client.upsert(collection_name=settings.qdrant_collection, points=points)
        logger.info("%d point Qdrant'a yazıldı.", len(points))


async def search_examples(
    query_vector: list[float],
    topic: str | None = None,
    sentiment: str | None = None,
    company_size: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    rating_min: float | None = None,
    rating_max: float | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Semantic search with optional metadata filters."""
    client = _get_client()

    conditions = []
    if topic:
        conditions.append(FieldCondition(key="topics", match=MatchAny(any=[topic])))
    if sentiment:
        conditions.append(FieldCondition(key="sentiment", match=MatchValue(value=sentiment)))
    if company_size:
        conditions.append(FieldCondition(key="company_size", match=MatchValue(value=company_size)))
    if rating_min is not None or rating_max is not None:
        conditions.append(
            FieldCondition(
                key="rating",
                range=Range(gte=rating_min, lte=rating_max),
            )
        )

    query_filter = Filter(must=conditions) if conditions else None

    # fetch more candidates when date filter is active; post-filter in Python
    fetch_limit = top_k * 10 if (date_from or date_to) else top_k

    hits = await client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        query_filter=query_filter,
        limit=fetch_limit,
        with_payload=True,
    )

    results = []
    for hit in hits.points:
        hit_date_str: str | None = hit.payload.get("date")
        if date_from and hit_date_str:
            if hit_date_str[:10] < date_from.isoformat():
                continue
        if date_to and hit_date_str:
            if hit_date_str[:10] > date_to.isoformat():
                continue
        results.append({
            "score": hit.score,
            "review_id": hit.payload.get("review_id"),
            "text": hit.payload.get("text"),
            "date": hit_date_str,
            "rating": hit.payload.get("rating"),
            "company_size": hit.payload.get("company_size"),
            "topics": hit.payload.get("topics"),
            "sentiment": hit.payload.get("sentiment"),
            "summary": hit.payload.get("summary"),
        })
        if len(results) >= top_k:
            break

    return results
