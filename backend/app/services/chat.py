import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

import anthropic
from sqlalchemy import Numeric, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.report import Report
from app.models.review import Review
from app.models.task import Task
from app.services.embedder import embed_text
from app.services.vector_store import search_examples as qdrant_search

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

_anthropic_client: anthropic.AsyncAnthropic | None = None


def _get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


async def close_client() -> None:
    global _anthropic_client
    if _anthropic_client is not None:
        await _anthropic_client.close()
        _anthropic_client = None

_TOPICS = [
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

_RATING_PROPS = {
    "rating_min": {
        "type": "number",
        "description": "Minimum puan filtresi (dahil). Örn: 4.0 → 4 yıldız ve üzeri.",
    },
    "rating_max": {
        "type": "number",
        "description": "Maksimum puan filtresi (dahil). Örn: 2.0 → 1-2 yıldız verenler.",
    },
}

_DATE_PROPS = {
    "date_from": {
        "type": "string",
        "description": "Başlangıç tarihi (dahil), YYYY-MM-DD formatında.",
    },
    "date_to": {
        "type": "string",
        "description": "Bitiş tarihi (dahil), YYYY-MM-DD formatında.",
    },
}

_VISUALIZE_PROPS = {
    "visualize": {
        "type": "boolean",
        "description": (
            "True ise bu tool çağrısının sonucu kullanıcıya grafik olarak gösterilir. "
            "Sadece kullanıcının doğrudan görmesi gereken ANA analiz sonuçlarını görselleştir. "
            "Araştırma / doğrulama amaçlı ara sorgularda false bırak. "
            "Bir yanıtta maksimum 2 grafik göster."
        ),
    },
    "chart_title": {
        "type": "string",
        "description": "visualize=true ise grafik başlığı. Kısa ve açıklayıcı yaz (örn: 'Veri Kalitesi — Negatif Trend').",
    },
}

_TOOLS = [
    {
        "name": "get_trend",
        "description": (
            "Seçilen döneme ait aylık review trendini getirir. "
            "Her satırda ay (YYYY-MM), ortalama puan ve review sayısı bulunur. "
            "Konu, tarih aralığı, sentiment, şirket büyüklüğü veya puan aralığına göre filtrelenebilir."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Konu filtresi. Belirtilmezse tüm konular dahil edilir.",
                    "enum": _TOPICS,
                },
                "sentiment": {
                    "type": "string",
                    "description": "Sentiment filtresi.",
                    "enum": ["pozitif", "negatif", "nötr"],
                },
                "company_size": {
                    "type": "string",
                    "description": (
                        "Şirket büyüklüğü filtresi. "
                        "Seçenekler: 'Small-Business (50 or fewer emp.)', "
                        "'Mid-Market (51-1000 emp.)', 'Enterprise (> 1000 emp.)', 'bilinmiyor'."
                    ),
                },
                **_DATE_PROPS,
                **_RATING_PROPS,
                **_VISUALIZE_PROPS,
            },
            "required": [],
        },
    },
    {
        "name": "get_breakdown",
        "description": (
            "Belirli bir boyuta göre review dağılımını getirir: "
            "konu başına kaç review, her segmentte ortalama puan gibi. "
            "group_by ile hangi boyutun kırılacağını belirt. "
            "O boyutun filtresini aynı anda kullanma (topic grup alırken topic filtresi gereksiz)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "description": "Hangi boyuta göre gruplanacak.",
                    "enum": ["topic", "sentiment", "company_size"],
                },
                "topic": {
                    "type": "string",
                    "description": "Konu filtresi (sadece group_by != 'topic' ise kullan).",
                    "enum": _TOPICS,
                },
                "sentiment": {
                    "type": "string",
                    "description": "Sentiment filtresi (sadece group_by != 'sentiment' ise kullan).",
                    "enum": ["pozitif", "negatif", "nötr"],
                },
                "company_size": {
                    "type": "string",
                    "description": "Şirket büyüklüğü filtresi (sadece group_by != 'company_size' ise kullan).",
                },
                **_DATE_PROPS,
                **_RATING_PROPS,
                **_VISUALIZE_PROPS,
            },
            "required": ["group_by"],
        },
    },
    {
        "name": "search_examples",
        "description": (
            "Review metinlerini getirir. "
            "Belirli bir dönemin, konunun veya sentiment'in review'larını listelemek, "
            "somut alıntı veya şikayet metni göstermek için kullan. "
            "Kullanıcı 'yorumları göster', 'yorumları getir', 'okumak istiyorum' dediğinde bu tool'u çağır. "
            "Konu, sentiment, şirket büyüklüğü, puan ve tarih aralığına göre filtrelenebilir. "
            "Tüm review'ları getirmek için top_k'yı büyük seç (örn: 50). "
            "Her sonuçta 'text' alanı asıl yorum içeriğini taşır."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Semantik arama sorgusu. İngilizce veya Türkçe olabilir. 'negative reviews' gibi genel bir sorgu da kullanılabilir.",
                },
                "topic": {
                    "type": "string",
                    "description": "Konu filtresi.",
                    "enum": _TOPICS,
                },
                "sentiment": {
                    "type": "string",
                    "description": "Sentiment filtresi.",
                    "enum": ["pozitif", "negatif", "nötr"],
                },
                "company_size": {
                    "type": "string",
                    "description": "Şirket büyüklüğü filtresi.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Kaç örnek getirileceği. Varsayılan: 5.",
                    "default": 5,
                },
                **_DATE_PROPS,
                **_RATING_PROPS,
                **_VISUALIZE_PROPS,
            },
            "required": ["query"],
        },
    },
]

_TOOLS += [
    {
        "name": "list_reports",
        "description": (
            "Sistemde üretilmiş ve kaydedilmiş aylık raporların listesini getirir. "
            "'Hangi ayların raporu var/işlendi/üretildi?' sorusu için kullan. "
            "Bu tool SADECE reporter.py tarafından üretilmiş raporları listeler — "
            "ham review verisi değil."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_report",
        "description": (
            "Belirtilen aya ait üretilmiş rapor metnini getirir. "
            "'X ayının raporuna bak', 'X raporu neler diyor', 'raporu göster' gibi ifadelerde kullan. "
            "Bu tool reporter.py çıktısını döner — ham review verisi değil."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {
                    "type": "string",
                    "description": "Rapor ayı YYYY-MM-01 formatında. Örn: '2026-04-01'",
                }
            },
            "required": ["month"],
        },
    },
    {
        "name": "get_report_notes",
        "description": (
            "Belirtilen aya ait PM'in rapora eklediği özel analizleri (notları) getirir. "
            "Bunlar PM'in chat üzerinden 'Rapora Ekle' ile eklediği soru-cevap çiftleridir; "
            "otomatik üretilen rapor metninin dışındadır. "
            "'Rapora ne ekledim?', 'Ekim notlarımda ne var?', 'Hangi analizleri raporladım?' gibi "
            "sorularda kullan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {
                    "type": "string",
                    "description": "Notların ait olduğu ay, YYYY-MM-01 formatında. Örn: '2025-10-01'",
                }
            },
            "required": ["month"],
        },
    },
]

_SYSTEM = (
    "Sen bir Product Intelligence asistanısın. "
    "Apollo.io hakkında G2'den toplanmış kullanıcı review verilerini analiz ediyorsun. "
    "Sorulara Türkçe yanıt ver. "
    "Sayısal ifadelerde kesin ol; veri yetersizse bunu açıkça belirt.\n\n"
    "ÖNEMLİ KAVRAM AYIRIMI:\n"
    "- 'Rapor' = reporter.py tarafından üretilmiş aylık ürün raporu (reports tablosu). "
    "  'Hangi ayların raporu var?', 'X raporuna bak' gibi sorularda list_reports veya get_report kullan.\n"
    "- 'PM notları / rapora eklenenler' = PM'in chat'ten 'Rapora Ekle' ile eklediği özel analizler (task_queue). "
    "  'Rapora ne ekledim?', 'Ekim notlarım', 'raporuma ne kaydettim?' gibi sorularda get_report_notes kullan.\n"
    "- 'Review verisi' = ham G2 review'ları (reviews + review_aggregates tabloları). "
    "  Trend, dağılım, grafik sorularında get_trend, get_breakdown, search_examples kullan.\n\n"
    "KRİTİK KURAL: Veri gerektiren her soruda mutlaka tool çağır. "
    "Hafızandan veya genel bilginden asla yanıt üretme.\n\n"
    "REVIEW LİSTELEME KURALI: Kullanıcı 'yorumları getir', 'göster', 'okumak istiyorum', 'listele' dediğinde "
    "search_examples'ı top_k=50 ile çağır. "
    "query parametresi için 'user reviews' yaz. "
    "Hiçbir zaman 'bu aracı bu amaç için kullanamam' deme — search_examples her zaman çalışır.\n\n"
    "GRAFİK KURALI: Her tool çağrısında visualize ve chart_title parametrelerini kendin belirle. "
    "Sadece kullanıcının doğrudan görmesi gereken ANA sonucu görselleştir (visualize=true). "
    "Araştırma veya doğrulama amaçlı ara sorgularda visualize=false bırak. "
    "Bir yanıtta maksimum 2 grafik göster."
)


@dataclass
class ChatResult:
    answer: str
    charts: list[dict] = field(default_factory=list)


# ── Tool implementations ─────────────────────────────────────────────────────


async def _execute_get_trend(args: dict, db: AsyncSession, sim_date: date | None = None) -> list[dict]:
    month_expr = func.date_trunc("month", Review.date)
    stmt = (
        select(
            month_expr.label("month"),
            func.round(func.avg(Review.rating).cast(Numeric(10, 2)), 2).label("avg_rating"),
            func.count().label("count"),
        )
        .where(Review.rating > 0)
        .group_by(month_expr)
        .order_by(month_expr)
    )

    if topic := args.get("topic"):
        stmt = stmt.where(Review.topics.contains([topic]))
    if sentiment := args.get("sentiment"):
        stmt = stmt.where(Review.sentiment == sentiment)
    if company_size := args.get("company_size"):
        stmt = stmt.where(Review.company_size == company_size)
    if date_from_str := args.get("date_from"):
        stmt = stmt.where(Review.date >= date.fromisoformat(date_from_str))
    date_to = date.fromisoformat(args["date_to"]) if args.get("date_to") else (
        sim_date - timedelta(days=1) if sim_date else None
    )
    if date_to:
        stmt = stmt.where(Review.date <= date_to)
    if rating_min := args.get("rating_min"):
        stmt = stmt.where(Review.rating >= float(rating_min))
    if rating_max := args.get("rating_max"):
        stmt = stmt.where(Review.rating <= float(rating_max))

    rows = (await db.execute(stmt)).fetchall()
    return [
        {"month": str(r.month)[:7], "avg_rating": float(r.avg_rating), "count": r.count}
        for r in rows
    ]


async def _execute_get_breakdown(args: dict, db: AsyncSession, sim_date: date | None = None) -> list[dict]:
    group_by = args["group_by"]

    if group_by == "topic":
        # PostgreSQL unnest — her review kendi konuları için bir satır üretir
        unnested = func.unnest(Review.topics)
        stmt = (
            select(
                unnested.label("group_value"),
                func.count().label("count"),
                func.round(func.avg(Review.rating).cast(Numeric(10, 2)), 2).label("avg_rating"),
            )
            .where(Review.rating > 0)
            .group_by(unnested)
            .order_by(func.count().desc())
        )
    elif group_by == "sentiment":
        group_expr = Review.sentiment
        stmt = (
            select(
                group_expr.label("group_value"),
                func.count().label("count"),
                func.round(func.avg(Review.rating).cast(Numeric(10, 2)), 2).label("avg_rating"),
            )
            .where(Review.rating > 0)
            .group_by(group_expr)
            .order_by(func.count().desc())
        )
    elif group_by == "company_size":
        group_expr = Review.company_size
        stmt = (
            select(
                group_expr.label("group_value"),
                func.count().label("count"),
                func.round(func.avg(Review.rating).cast(Numeric(10, 2)), 2).label("avg_rating"),
            )
            .where(Review.rating > 0)
            .group_by(group_expr)
            .order_by(func.count().desc())
        )
    else:
        return [{"error": f"Geçersiz group_by: {group_by}"}]

    if group_by != "topic":
        if topic := args.get("topic"):
            stmt = stmt.where(Review.topics.contains([topic]))
    if group_by != "sentiment":
        if sentiment := args.get("sentiment"):
            stmt = stmt.where(Review.sentiment == sentiment)
    if group_by != "company_size":
        if company_size := args.get("company_size"):
            stmt = stmt.where(Review.company_size == company_size)
    if date_from_str := args.get("date_from"):
        stmt = stmt.where(Review.date >= date.fromisoformat(date_from_str))
    date_to = date.fromisoformat(args["date_to"]) if args.get("date_to") else (
        sim_date - timedelta(days=1) if sim_date else None
    )
    if date_to:
        stmt = stmt.where(Review.date <= date_to)
    if rating_min := args.get("rating_min"):
        stmt = stmt.where(Review.rating >= float(rating_min))
    if rating_max := args.get("rating_max"):
        stmt = stmt.where(Review.rating <= float(rating_max))

    rows = (await db.execute(stmt)).fetchall()
    return [
        {
            "group_value": str(r.group_value) if r.group_value else "bilinmiyor",
            "count": r.count,
            "avg_rating": float(r.avg_rating) if r.avg_rating else None,
        }
        for r in rows
    ]


async def _execute_list_reports(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(Report).order_by(Report.month))).scalars().all()
    return [{"month": str(r.month)[:7], "created_at": str(r.created_at)[:10]} for r in rows]


async def _execute_get_report(args: dict, db: AsyncSession) -> dict:
    try:
        month = date.fromisoformat(args["month"]).replace(day=1)
    except (ValueError, KeyError):
        return {"error": "Geçersiz tarih formatı. YYYY-MM-01 kullan."}
    row = (
        await db.execute(select(Report).where(Report.month == month))
    ).scalar_one_or_none()
    if not row:
        return {"error": f"{str(month)[:7]} ayına ait rapor bulunamadı. list_reports ile mevcut raporları kontrol et."}
    return {"month": str(row.month)[:7], "content": row.content}


async def _execute_get_report_notes(args: dict, db: AsyncSession) -> list[dict]:
    try:
        month = date.fromisoformat(args["month"]).replace(day=1)
    except (ValueError, KeyError):
        return [{"error": "Geçersiz tarih formatı. YYYY-MM-01 kullan."}]
    rows = (
        await db.execute(
            select(Task)
            .where(Task.target_date == month, Task.status == "tamamlandı", Task.result.isnot(None))
            .order_by(Task.created_at)
        )
    ).scalars().all()
    if not rows:
        return [{"info": f"{str(month)[:7]} ayına ait PM notu bulunamadı."}]
    return [{"soru": t.prompt, "cevap": t.result} for t in rows]


async def _execute_search_examples(args: dict, sim_date: date | None = None) -> list[dict]:
    query_vector = await embed_text(args["query"])

    date_from = date.fromisoformat(args["date_from"]) if args.get("date_from") else None
    date_to = date.fromisoformat(args["date_to"]) if args.get("date_to") else (
        sim_date - timedelta(days=1) if sim_date else None
    )

    results = await qdrant_search(
        query_vector=query_vector,
        topic=args.get("topic"),
        sentiment=args.get("sentiment"),
        company_size=args.get("company_size"),
        date_from=date_from,
        date_to=date_to,
        rating_min=args.get("rating_min"),
        rating_max=args.get("rating_max"),
        top_k=args.get("top_k", 5),
    )
    return [
        {
            "date": r.get("date"),
            "rating": r.get("rating"),
            "company_size": r.get("company_size"),
            "topics": r.get("topics"),
            "sentiment": r.get("sentiment"),
            "summary": r.get("summary"),
            "text": r.get("text"),
        }
        for r in results
    ]


# ── Main entry point ─────────────────────────────────────────────────────────


async def answer(message: str, db: AsyncSession, simulated_date: str | None = None) -> ChatResult:
    """
    Sends user message to Claude with tools available.
    Returns answer text + structured chart data for each tool call made.
    """
    sim_date: date | None = None
    system = _SYSTEM
    if simulated_date:
        try:
            sim_date = date.fromisoformat(simulated_date)
        except ValueError:
            pass
        cutoff = str(sim_date - timedelta(days=1)) if sim_date else simulated_date
        system += (
            f"\n\nMevcut simüle tarih: {simulated_date}. "
            f"Yalnızca {cutoff} tarihine kadar olan review verilerine erişebilirsin. "
            f"Bu tarihten sonrasını bilmiyorsun — tarih filtresi vermesen de sistem otomatik kısıtlar. "
            f"Veri seti Temmuz 2025 (2025-07) ile başlar; bu aydan önce hiç review verisi yoktur."
        )

    client = _get_anthropic_client()
    messages: list[dict] = [{"role": "user", "content": message}]
    all_charts: list[dict] = []

    response = await client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=system,
        tools=_TOOLS,
        messages=messages,
    )

    for _ in range(3):
        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            logger.info("Tool: %s args=%s", block.name, block.input)
            try:
                if block.name == "get_trend":
                    result = await _execute_get_trend(block.input, db, sim_date)
                    if block.input.get("visualize"):
                        all_charts.append({
                            "type": "trend",
                            "title": block.input.get("chart_title", ""),
                            "data": result,
                        })
                elif block.name == "get_breakdown":
                    result = await _execute_get_breakdown(block.input, db, sim_date)
                    if block.input.get("visualize"):
                        all_charts.append({
                            "type": "breakdown",
                            "group_by": block.input.get("group_by"),
                            "title": block.input.get("chart_title", ""),
                            "data": result,
                        })
                elif block.name == "search_examples":
                    result = await _execute_search_examples(block.input, sim_date)
                    if block.input.get("visualize"):
                        all_charts.append({
                            "type": "examples",
                            "title": block.input.get("chart_title", ""),
                            "data": result,
                        })
                elif block.name == "list_reports":
                    result = await _execute_list_reports(db)
                elif block.name == "get_report":
                    result = await _execute_get_report(block.input, db)
                elif block.name == "get_report_notes":
                    result = await _execute_get_report_notes(block.input, db)
                else:
                    result = {"error": f"Bilinmeyen tool: {block.name}"}
            except Exception as exc:
                logger.error("Tool hatası (%s): %s", block.name, exc)
                result = {"error": str(exc)}

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = await client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=system,
            tools=_TOOLS,
            messages=messages,
        )

    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    answer_text = "\n".join(text_blocks) if text_blocks else "Yanıt alınamadı."
    return ChatResult(answer=answer_text, charts=all_charts)
