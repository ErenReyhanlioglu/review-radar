import json
import logging
import uuid
from datetime import date
from dateutil.relativedelta import relativedelta

import anthropic
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.aggregate import ReviewAggregate
from app.models.report import Report
from app.models.review import Review

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"


# ── Data collection helpers ───────────────────────────────────────────────────


async def _collect_metrics(month: date, db: AsyncSession) -> dict:
    """Current month vs previous month rating metrics."""
    prev_month = month - relativedelta(months=1)

    async def _month_data(m: date) -> dict:
        start = m.replace(day=1)
        end = date(m.year + 1, 1, 1) if m.month == 12 else date(m.year, m.month + 1, 1)
        rows = (
            await db.execute(
                select(Review.rating, func.count().label("cnt"))
                .where(Review.date >= start, Review.date < end, Review.rating > 0)
                .group_by(Review.rating)
                .order_by(Review.rating)
            )
        ).fetchall()
        total = sum(r.cnt for r in rows)
        avg = round(sum(r.rating * r.cnt for r in rows) / total, 2) if total else 0
        all_values = ["1", "1.5", "2", "2.5", "3", "3.5", "4", "4.5", "5"]
        raw: dict[str, int] = {}
        for r in rows:
            f = float(r.rating)
            key = str(int(f)) if f == int(f) else str(f)
            raw[key] = r.cnt
        dist = {v: raw.get(v, 0) for v in all_values}
        return {"total": total, "avg_rating": avg, "distribution": dist}

    return {
        "current": await _month_data(month),
        "previous": await _month_data(prev_month),
    }


async def _collect_sentiment(month: date, db: AsyncSession) -> dict:
    """Per-review sentiment counts: current and previous month."""
    prev_month = month - relativedelta(months=1)

    async def _query(start: date, end: date) -> dict:
        rows = (
            await db.execute(
                select(Review.sentiment, func.count().label("cnt"))
                .where(Review.date >= start, Review.date < end, Review.sentiment.isnot(None))
                .group_by(Review.sentiment)
            )
        ).fetchall()
        return {r.sentiment: int(r.cnt) for r in rows}

    cur_start = month.replace(day=1)
    cur_end = date(month.year + 1, 1, 1) if month.month == 12 else date(month.year, month.month + 1, 1)
    prev_start = prev_month.replace(day=1)

    return {
        "current": await _query(cur_start, cur_end),
        "previous": await _query(prev_start, cur_start),
    }


async def _collect_topics(month: date, db: AsyncSession) -> dict:
    """Topic × sentiment counts: current and previous month."""
    prev_month = month - relativedelta(months=1)

    async def _query(m: date) -> dict:
        rows = (
            await db.execute(
                select(
                    ReviewAggregate.topic,
                    ReviewAggregate.sentiment,
                    func.sum(ReviewAggregate.count).label("cnt"),
                )
                .where(ReviewAggregate.month == m.replace(day=1))
                .group_by(ReviewAggregate.topic, ReviewAggregate.sentiment)
                .order_by(func.sum(ReviewAggregate.count).desc())
            )
        ).fetchall()
        result: dict[str, dict] = {}
        for r in rows:
            if r.topic not in result:
                result[r.topic] = {"pozitif": 0, "negatif": 0, "nötr": 0, "toplam": 0}
            result[r.topic][r.sentiment] = int(r.cnt)
            result[r.topic]["toplam"] += int(r.cnt)
        return result

    return {
        "current": await _query(month),
        "previous": await _query(prev_month),
    }


async def _collect_topic_sentiment(month: date, db: AsyncSession) -> dict:
    """Aggregate sentiment across all topic mentions: current and previous month."""
    prev_month = month - relativedelta(months=1)

    async def _query(m: date) -> dict:
        rows = (
            await db.execute(
                select(ReviewAggregate.sentiment, func.sum(ReviewAggregate.count).label("cnt"))
                .where(ReviewAggregate.month == m.replace(day=1))
                .group_by(ReviewAggregate.sentiment)
            )
        ).fetchall()
        return {r.sentiment: int(r.cnt) for r in rows}

    return {
        "current": await _query(month),
        "previous": await _query(prev_month),
    }


async def _collect_segments(month: date, db: AsyncSession) -> dict:
    """Company size breakdown: current and previous month (each review counted once)."""
    prev_month = month - relativedelta(months=1)

    async def _query(start: date, end: date) -> dict:
        rows = (
            await db.execute(
                select(Review.company_size, func.count().label("cnt"))
                .where(Review.date >= start, Review.date < end)
                .group_by(Review.company_size)
                .order_by(func.count().desc())
            )
        ).fetchall()
        return {(r.company_size or "bilinmiyor"): int(r.cnt) for r in rows}

    cur_start = month.replace(day=1)
    cur_end = date(month.year + 1, 1, 1) if month.month == 12 else date(month.year, month.month + 1, 1)
    prev_start = prev_month.replace(day=1)

    return {
        "current": await _query(cur_start, cur_end),
        "previous": await _query(prev_start, cur_start),
    }


async def _collect_trend(month: date, db: AsyncSession) -> list[dict]:
    """Last 6 months avg_rating + count trend."""
    from sqlalchemy import Numeric
    six_months_ago = month - relativedelta(months=5)
    month_expr = func.date_trunc("month", Review.date)
    rows = (
        await db.execute(
            select(
                month_expr.label("month"),
                func.round(func.avg(Review.rating).cast(Numeric(10, 2)), 2).label("avg_rating"),
                func.count().label("count"),
            )
            .where(Review.rating > 0, Review.date >= six_months_ago.replace(day=1))
            .group_by(month_expr)
            .order_by(month_expr)
        )
    ).fetchall()
    return [
        {"month": str(r.month)[:7], "avg_rating": float(r.avg_rating), "count": r.count}
        for r in rows
    ]


# ── Report generation ─────────────────────────────────────────────────────────


def _pct(n: int, total: int) -> str:
    return f"{round(n / total * 100, 1)}%" if total else "0%"


def _delta(cur: int | float, prev: int | float) -> str:
    d = round(cur - prev, 2) if isinstance(cur, float) or isinstance(prev, float) else cur - prev
    return f"+{d}" if d > 0 else str(d)


def _build_prompt(
    month: date,
    metrics: dict,
    sentiment: dict,
    topics: dict,
    topic_sentiment: dict,
    segments: dict,
    trend: list[dict],
) -> str:
    cur_m = metrics["current"]
    prev_m = metrics["previous"]
    has_prev = prev_m["total"] > 0
    prev_label = month.strftime("%B %Y") + " öncesi ay"

    # ── Sentiment table rows ──────────────────────────────────────────────────
    cur_s = sentiment["current"]
    prev_s = sentiment["previous"]
    cur_s_total = sum(cur_s.values())
    prev_s_total = sum(prev_s.values())
    has_prev_s = bool(prev_s)

    def _sent_row(key: str, label: str) -> str:
        c = cur_s.get(key, 0)
        c_str = f"{c} ({_pct(c, cur_s_total)})"
        if has_prev_s:
            p = prev_s.get(key, 0)
            return f"| {label} | {c_str} | {p} ({_pct(p, prev_s_total)}) | {_delta(c, p)} |"
        return f"| {label} | {c_str} | - | - |"

    sentiment_rows = "\n".join([
        _sent_row("pozitif", "Pozitif"),
        _sent_row("negatif", "Negatif"),
        _sent_row("nötr", "Nötr"),
        f"| **Toplam** | **{cur_s_total}** | **{prev_s_total if has_prev_s else '-'}** | **{_delta(cur_s_total, prev_s_total) if has_prev_s else '-'}** |",
    ])

    # ── Topic sentiment table rows ────────────────────────────────────────────
    cur_ts = topic_sentiment["current"]
    prev_ts = topic_sentiment["previous"]
    cur_ts_total = sum(cur_ts.values())
    prev_ts_total = sum(prev_ts.values())
    has_prev_ts = bool(prev_ts)

    def _ts_row(key: str, label: str) -> str:
        c = cur_ts.get(key, 0)
        c_str = f"{c} ({_pct(c, cur_ts_total)})"
        if has_prev_ts:
            p = prev_ts.get(key, 0)
            return f"| {label} | {c_str} | {p} ({_pct(p, prev_ts_total)}) | {_delta(c, p)} |"
        return f"| {label} | {c_str} | - | - |"

    topic_sentiment_rows = "\n".join([
        _ts_row("pozitif", "Pozitif"),
        _ts_row("negatif", "Negatif"),
        _ts_row("nötr", "Nötr"),
        f"| **Toplam** | **{cur_ts_total}** | **{prev_ts_total if has_prev_ts else '-'}** | **{_delta(cur_ts_total, prev_ts_total) if has_prev_ts else '-'}** |",
    ])

    # ── Segment table rows ────────────────────────────────────────────────────
    cur_seg = segments["current"]
    prev_seg = segments["previous"]
    cur_seg_total = sum(cur_seg.values())
    prev_seg_total = sum(prev_seg.values())
    has_prev_seg = bool(prev_seg)

    _SEG_LABELS = {
        "Small-Business (50 or fewer emp.)": "Küçük İşletme (≤50)",
        "Mid-Market (51-1000 emp.)": "Orta Pazar (51–1.000)",
        "Enterprise (> 1000 emp.)": "Kurumsal (>1.000)",
        "bilinmiyor": "Bilinmiyor",
    }
    all_seg_keys = list(dict.fromkeys(list(cur_seg.keys()) + list(prev_seg.keys())))

    def _seg_row(key: str) -> str:
        label = _SEG_LABELS.get(key, key)
        c = cur_seg.get(key, 0)
        c_str = f"{c} ({_pct(c, cur_seg_total)})"
        if has_prev_seg:
            p = prev_seg.get(key, 0)
            return f"| {label} | {c_str} | {p} ({_pct(p, prev_seg_total)}) | {_delta(c, p)} |"
        return f"| {label} | {c_str} | - | - |"

    segment_rows = "\n".join(
        [_seg_row(k) for k in all_seg_keys]
        + [f"| **Toplam** | **{cur_seg_total}** | **{prev_seg_total if has_prev_seg else '-'}** | **{_delta(cur_seg_total, prev_seg_total) if has_prev_seg else '-'}** |"]
    )

    # ── Metrics table rows ────────────────────────────────────────────────────
    def _met_row(label: str, cur_val: str, prev_val: str, delta: str) -> str:
        return f"| {label} | {cur_val} | {prev_val} | {delta} |"

    all_stars = ["1", "1.5", "2", "2.5", "3", "3.5", "4", "4.5", "5"]
    star_rows = []
    for v in reversed(all_stars):
        c = cur_m["distribution"].get(v, 0)
        p = prev_m["distribution"].get(v, 0) if has_prev else None
        c_str = f"{c} ({_pct(c, cur_m['total'])})"
        p_str = f"{p} ({_pct(p, prev_m['total'])})" if p is not None else "-"
        d_str = _delta(c, p) if p is not None else "-"
        star_rows.append(_met_row(f"{v}★", c_str, p_str, d_str))

    metrics_rows = "\n".join([
        _met_row(
            "İnceleme Sayısı",
            str(cur_m["total"]),
            str(prev_m["total"]) if has_prev else "-",
            _delta(cur_m["total"], prev_m["total"]) if has_prev else "-",
        ),
        _met_row(
            "Ortalama Puan",
            f"{cur_m['avg_rating']}★",
            f"{prev_m['avg_rating']}★" if has_prev else "-",
            _delta(cur_m["avg_rating"], prev_m["avg_rating"]) if has_prev else "-",
        ),
    ] + star_rows)

    # ── Topic analysis context ────────────────────────────────────────────────
    cur_topics = topics["current"]
    top_complaints = sorted(
        [(t, d["negatif"]) for t, d in cur_topics.items() if d["negatif"] > 0],
        key=lambda x: -x[1],
    )[:5]
    top_praised = sorted(
        [(t, d["pozitif"]) for t, d in cur_topics.items() if d["pozitif"] > 0],
        key=lambda x: -x[1],
    )[:5]

    return f"""
Sen bir Product Intelligence analistsin. Aşağıdaki Apollo.io G2 review verilerinden {month.strftime('%B %Y')} için profesyonel bir aylık ürün raporu yaz.

Rapor Türkçe olmalı. Başlıkları markdown formatında yaz. Kesin sayılara dayanarak yorum yap; yorumlarında veriye referans ver.

## Ham Veriler

### Metrikler (Bu Ay / Geçen Ay)
Bu ay: {cur_m['total']} review, {cur_m['avg_rating']}★
Geçen ay: {prev_m['total']} review, {prev_m['avg_rating']}★ {"(veri yok — ilk ay)" if not has_prev else ""}

### Sentiment Dağılımı (per-review)
Bu ay: {json.dumps(cur_s, ensure_ascii=False)}
Geçen ay: {json.dumps(prev_s, ensure_ascii=False) if has_prev_s else "(veri yok)"}

### Konu Duygu Dağılımı (mention toplamları — bir review birden fazla konuya değinebilir)
Bu ay: {json.dumps(cur_ts, ensure_ascii=False)}
Geçen ay: {json.dumps(prev_ts, ensure_ascii=False) if has_prev_ts else "(veri yok)"}

### Konu × Sentiment
Bu ay en çok şikayet: {top_complaints}
Bu ay en çok övgü: {top_praised}
Detay: {json.dumps(cur_topics, ensure_ascii=False, indent=2)}

### Segment Dağılımı
Bu ay: {json.dumps(cur_seg, ensure_ascii=False)}
Geçen ay: {json.dumps(prev_seg, ensure_ascii=False) if has_prev_seg else "(veri yok)"}

### Son 6 Aylık Trend
{json.dumps(trend, ensure_ascii=False)}

---

Raporun şu bölümleri içermeli (bu başlıkları AYNEN kullan):

## Bu Ay Öne Çıkanlar
2-3 cümle özet.

## Metrikler
Aşağıdaki tabloyu AYNEN bu formatta yaz. Geçen ay verisi yoksa "-" kullan. 5★'dan 1★'a sıralı yaz. Tüm yarım yıldız değerleri dahil, 0 olanlar da gösterilmeli.

| Metrik | Bu Ay | Geçen Ay | Δ |
|--------|-------|----------|---|
{metrics_rows}

Tablodan sonra kısa yorum: puan değişimi ve trend.

## Konu Analizi
En çok şikayet ve övülen konular. Konu duygu dağılımı tablosunu AYNEN bu formatta yaz:

| Sentiment | Bu Ay | Geçen Ay | Δ |
|-----------|-------|----------|---|
{topic_sentiment_rows}

Not: konu toplamları review sayısını aşabilir çünkü bir review birden fazla konuya değinebilir.

## Sentiment Analizi
Genel sentiment dağılımını AYNEN bu formatta yaz:

| Sentiment | Bu Ay | Geçen Ay | Δ |
|-----------|-------|----------|---|
{sentiment_rows}

Her review tek bir sentiment alır; toplam = o ayın review sayısı.

## Segment Analizi
Şirket büyüklüğü dağılımını AYNEN bu formatta yaz:

| Segment | Bu Ay | Geçen Ay | Δ |
|---------|-------|----------|---|
{segment_rows}

Her review tek bir firmaya ait; Toplam = o ayın review sayısı.

## Aksiyon Önerileri
Veriden türetilmiş, somut 3 madde.

Veri yetersizse (az review) bunu açıkça belirt. Spekülasyon yapma.
"""


async def generate_report(month: date, db: AsyncSession) -> str:
    """Generates and saves the monthly report. Returns the markdown content."""
    logger.info("Rapor üretiliyor: %s", month)

    metrics, sentiment, topics, topic_sentiment, segments, trend = (
        await _collect_metrics(month, db),
        await _collect_sentiment(month, db),
        await _collect_topics(month, db),
        await _collect_topic_sentiment(month, db),
        await _collect_segments(month, db),
        await _collect_trend(month, db),
    )

    prompt = _build_prompt(month, metrics, sentiment, topics, topic_sentiment, segments, trend)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.content[0].text

    stmt = (
        pg_insert(Report)
        .values(id=uuid.uuid4(), month=month.replace(day=1), content=content)
        .on_conflict_do_update(index_elements=["month"], set_={"content": content})
    )
    await db.execute(stmt)
    await db.commit()
    logger.info("Rapor kaydedildi: %s", month)

    return content
