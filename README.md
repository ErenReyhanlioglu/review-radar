# Review Radar

Apollo.io ürün departmanı için G2 review'larını otomatik olarak analiz eden, haftalık raporlar üreten ve PM'lere AI destekli insight sunan bir Product Intelligence sistemi.

## Özellikler

- **Otomatik veri toplama** — Her Pazartesi Apify üzerinden G2'den incremental scraping
- **AI analizi** — Claude API ile konu etiketleme, sentiment analizi ve özetleme
- **Semantik arama** — Qdrant vector store üzerinde doğal dil sorguları
- **Trend analizi** — PostgreSQL aggregation tabloları ile haftalık/aylık trend grafikler
- **AI chat** — Tool calling ile PM'lerin analitik sorularını anlık yanıtlama
- **Haftalık rapor** — PM sorgularını birleştirerek SendGrid ile otomatik email

## Tech Stack

| Katman | Teknoloji |
|--------|-----------|
| Scraping | Apify — G2 Scraper (incremental) |
| Embedding | OpenAI text-embedding-3-small |
| Vector Store | Qdrant |
| AI | Claude API — claude-sonnet-4-6 |
| Backend | FastAPI |
| Frontend | React + Recharts |
| Veritabanı | PostgreSQL |
| Email | SendGrid |
| Zamanlayıcı | APScheduler |
| Deploy | Hugging Face Spaces |

## Kurulum

### Gereksinimler

- Python 3.11+
- Node.js 18+
- uv
- PostgreSQL
- Qdrant

### Backend

```bash
cd backend
uv sync
cp .env.example .env
# .env dosyasını kendi API key'lerinizle doldurun
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Mimari

Detaylı sistem mimarisi ve veri akışı için:
- [`workflow-diagram.md`](workflow-diagram.md) — Sistem akışı
- [`structure-diagram.md`](structure-diagram.md) — Klasör ve kod yapısı

## Lisans

MIT
