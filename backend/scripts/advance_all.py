"""
Tüm ayları sırayla işler: her advance sonrası pipeline bitene kadar bekler.
Kullanım: uv run python scripts/advance_all.py
"""
import asyncio
import httpx

BASE = "http://localhost:8001"
TARGET_DATE = "2026-07-01"  # Bu tarihe ulaşınca tüm veriler işlenmiş demek


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            # Mevcut durumu al
            status = (await client.get(f"{BASE}/simulation/status")).json()
            current = status["simulated_date"]
            running = status.get("is_running", False)

            if running:
                print(f"  Pipeline çalışıyor, bekleniyor... ({current})")
                await asyncio.sleep(20)
                continue

            if current >= TARGET_DATE:
                print(f"\n✓ Tüm aylar işlendi. Son tarih: {current}")
                break

            # Bir sonraki ayı başlat
            print(f"\n→ Advance: {current} → sonraki ay...")
            r = await client.post(f"{BASE}/simulation/advance")
            print(f"  {r.json()}")

            # Pipeline'ın başlaması için kısa bekle
            await asyncio.sleep(5)

            # Pipeline bitene kadar bekle (her 20 saniyede kontrol)
            while True:
                await asyncio.sleep(20)
                status = (await client.get(f"{BASE}/simulation/status")).json()
                print(f"  Durum: is_running={status.get('is_running')}  tarih={status['simulated_date']}")
                if not status.get("is_running", False):
                    print(f"  ✓ Ay tamamlandı: {status['simulated_date']}")
                    break


if __name__ == "__main__":
    asyncio.run(main())
