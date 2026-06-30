"""Eksik aylık raporları üretir."""
import asyncio
from datetime import date
from sqlalchemy import text
from app.api.deps import AsyncSessionLocal
from app.services.reporter import generate_report


async def main():
    months = [
        date(2025, 7, 1),
        date(2025, 8, 1),
        date(2025, 9, 1),
        date(2025, 10, 1),
        date(2025, 11, 1),
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
        date(2026, 4, 1),
        date(2026, 5, 1),
        date(2026, 6, 1),
    ]

    async with AsyncSessionLocal() as db:
        # Mevcut raporları bul
        r = await db.execute(text("SELECT month FROM reports"))
        existing = {row[0] for row in r.fetchall()}
        print(f"Mevcut rapor sayisi: {len(existing)}")

        missing = [m for m in months if m not in existing]
        print(f"Eksik rapor sayisi: {len(missing)}\n")

        for month in missing:
            print(f"-> {month} raporu uretiliyor...")
            try:
                content = await generate_report(month, db)
                print(f"   OK ({len(content)} karakter)\n")
            except Exception as e:
                print(f"   HATA: {e}\n")

    print("Tamamlandi.")


if __name__ == "__main__":
    asyncio.run(main())
