# Review Radar

**Apollo.io için G2 review'larını analiz eden Product Intelligence PoC'u.**

PM iş akışını otomatize etmek üzerine geliştirilmiş bir case study: aylık review pipeline'ı, AI destekli analiz ve PM'e özel rapor üretimi.

![Review Radar Dashboard](frontend/src/assets/hero.png)

---

## Arka Plan

Bir PM'in aylık rutini şöyle işler: G2/Capterra gibi platformlardan review topla, konu ve sentiment analizi yap, trend çiz, rapor yaz, ekiple paylaş. Bu süreç tekrarlı ve zaman alıcı.

Review Radar bu sürecin tamamını otomatize eder. Gerçek bir scraper yerine simülasyon kullanır — "Sonraki Ay" butonuna her basışta sistem o ayın review'larını ilk kez görüyormuş gibi işler, rapor üretir ve chat üzerinden anlık sorgulara yanıt verir.

---

## Nasıl Çalışır

```
"Sonraki Ay" butonu
        ↓
loader.py      → reviews_clean.json'dan o ayın review'larını filtreler
processor.py   → Claude API ile konu etiketi + sentiment + özet
embedder.py    → OpenAI text-embedding-3-small ile vektör üretir
vector_store.py → Qdrant'a upsert eder
aggregator.py  → PostgreSQL review_aggregates tablosunu günceller
reporter.py    → Claude API ile aylık rapor markdown'ı üretir
mailer.py      → SendGrid ile ilgili kişilere iletir
```

Simülasyon tarihi `system_config` tablosunda tutulur. Her ay bağımsız işlenir.

---

## Özellikler

- **Simüle aylık pipeline** — Zaman ilerletilerek gerçek bir cron/scraper olmadan uçtan uca test edilebilir
- **AI enrichment** — Claude API ile her review'a konu etiketleri, sentiment ve özet atanır
- **Semantik arama** — Qdrant üzerinde doğal dil sorguları; "fiyat şikayeti olan enterprise müşteriler" gibi
- **AI chat (tool calling)** — PM, trend/dağılım/örnek review sorgusu atabilir; Claude hangi tool'u çağıracağına kendisi karar verir
- **Rapora ekle** — Chat'te beğenilen analizler "Rapora Ekle" ile bir sonraki raporun PM bölümüne eklenir
- **Otomatik aylık rapor** — Metrikler, konu analizi, sentiment, segment ve aksiyon önerileri içeren markdown rapor
- **Email gönderimi** — SendGrid entegrasyonu; rapor doğrudan dashboard'dan gönderilebilir
- **Viewer modu** — `?mode=viewer` parametresiyle salt okunur paylaşım linki

---

## Tech Stack

| Katman | Teknoloji |
|--------|-----------|
| Backend | FastAPI + Python 3.11 |
| AI (enrichment & rapor) | Claude API — Haiku 4.5 |
| AI (chat) | Claude API — Haiku 4.5, tool calling |
| Embedding | OpenAI text-embedding-3-small |
| Vector Store | Qdrant |
| Veritabanı | PostgreSQL + SQLAlchemy async |
| Migration | Alembic |
| Frontend | React + TypeScript + Recharts |
| Email | SendGrid |
| Paket yönetimi | uv |

---

## Veri Seti

G2'den derlenmiş **770 Apollo.io review**'ı (Temmuz 2025 – Haziran 2026). `backend/data/reviews_clean.json` — git'e girmez.

Konu etiket listesi: `veri kalitesi`, `fiyat`, `email deliverability`, `UX / kullanım kolaylığı`, `müşteri desteği`, `entegrasyon`, `arama & filtreleme`, `otomasyon`, `raporlama & analitik`, `genel olumlu`

---

## Kurulum

### Gereksinimler

- Python 3.11+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv)
- PostgreSQL
- Qdrant

### Backend

```bash
cd backend
uv sync
cp .env.example .env
# .env dosyasını doldurun (ANTHROPIC_API_KEY, OPENAI_API_KEY, DATABASE_URL, ...)
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Simülasyon API'si

| Endpoint | Açıklama |
|----------|----------|
| `POST /simulation/advance` | Simüle tarihi 1 ay ileri sar, pipeline'ı tetikle |
| `GET /simulation/status` | Mevcut simüle tarih ve pipeline durumu |
| `POST /simulation/reset` | Başa sar |

---

## Dokümantasyon

| Dosya | İçerik |
|-------|--------|
| [`workflow-diagram.md`](workflow-diagram.md) | Sistem akışı ve veri pipeline'ı |
| [`structure-diagram.md`](structure-diagram.md) | Klasör yapısı ve API endpoint'leri |
| [`dataset-diagram.md`](dataset-diagram.md) | Veri seti şeması ve tablo ilişkileri |
| [`product-report-abstract.md`](product-report-abstract.md) | Aylık rapor yapısı ve PM iş akışı |

---

## Lisans

MIT
