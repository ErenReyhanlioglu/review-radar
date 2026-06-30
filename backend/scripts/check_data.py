import asyncio
from sqlalchemy import text
from app.api.deps import AsyncSessionLocal


async def check():
    async with AsyncSessionLocal() as db:

        # 1. Reviews tablosu - aylık özet
        print("=== REVIEWS (aylık) ===")
        r = await db.execute(text("""
            SELECT
                date_trunc('month', date)::date as ay,
                COUNT(*) as sayi,
                ROUND(AVG(rating)::numeric, 2) as ort_puan,
                COUNT(CASE WHEN sentiment='pozitif' THEN 1 END) as poz,
                COUNT(CASE WHEN sentiment='negatif' THEN 1 END) as neg,
                COUNT(CASE WHEN sentiment='nötr' THEN 1 END) as notr,
                COUNT(CASE WHEN topics IS NULL OR topics='{}' THEN 1 END) as topic_eksik
            FROM reviews
            WHERE rating > 0
            GROUP BY ay ORDER BY ay
        """))
        rows = r.fetchall()
        toplam = 0
        print(f"{'Ay':<12} {'Sayı':>5} {'Ort':>5} {'Poz':>4} {'Neg':>4} {'Nötr':>5} {'TopicEksik':>10}")
        print("-" * 55)
        for row in rows:
            print(f"{str(row.ay):<12} {row.sayi:>5} {float(row.ort_puan):>5.2f} {row.poz:>4} {row.neg:>4} {row.notr:>5} {row.topic_eksik:>10}")
            toplam += row.sayi
        print(f"{'TOPLAM':<12} {toplam:>5}")

        # 2. Review aggregates - aylık toplam count
        print("\n=== REVIEW_AGGREGATES (aylık toplam) ===")
        r = await db.execute(text("""
            SELECT month, SUM(count) as toplam
            FROM review_aggregates
            GROUP BY month ORDER BY month
        """))
        for row in r.fetchall():
            print(f"  {row.month}  ->  {row.toplam}")

        # 3. Reports tablosu
        print("\n=== REPORTS ===")
        r = await db.execute(text("""
            SELECT month, LENGTH(content) as karakter
            FROM reports ORDER BY month
        """))
        rows = r.fetchall()
        print(f"Rapor sayisi: {len(rows)}")
        for row in rows:
            print(f"  {row.month}  ->  {row.karakter} karakter")

        # 4. Duplikat kontrolü
        print("\n=== DUPLIKAT KONTROLU ===")
        r = await db.execute(text("""
            SELECT review_id, COUNT(*) as adet
            FROM reviews
            GROUP BY review_id
            HAVING COUNT(*) > 1
        """))
        dups = r.fetchall()
        print(f"Duplikat review: {len(dups)}" + (" OK" if not dups else " <- SORUN"))

        # 5. Boş summary
        print("\n=== FALLBACK ALAN REVIEWLAR ===")
        r = await db.execute(text("""
            SELECT COUNT(*) FROM reviews WHERE summary = '' OR summary IS NULL
        """))
        print(f"Bos summary (fallback): {r.scalar()}")

        # 6. Qdrant point sayısı
        print("\n=== QDRANT ===")
        from app.services.vector_store import _get_client
        from app.config import settings
        c = _get_client()
        info = await c.get_collection(settings.qdrant_collection)
        print(f"Qdrant points: {info.points_count}")
        await c.close()


asyncio.run(check())
