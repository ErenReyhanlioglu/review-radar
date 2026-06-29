# Apollo.io Product Review Intelligence System
## Proje Klasör & Kod Yapısı

---

## KLASÖR YAPISI

```
review-radar/
│
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app, lifespan, CORS
│   │   ├── config.py                   # Pydantic Settings (.env okur)
│   │   │
│   │   ├── api/                        # Sadece HTTP katmanı
│   │   │   ├── deps.py                 # DB session, dependency injection
│   │   │   └── routes/
│   │   │       ├── chat.py             # POST /chat
│   │   │       ├── charts.py           # GET /charts/trend, /charts/topics ...
│   │   │       └── tasks.py            # POST /tasks, GET /tasks
│   │   │
│   │   ├── services/                   # İş mantığı — route'lardan bağımsız
│   │   │   ├── scraper.py              # Apify API çağrısı + incremental filtre
│   │   │   ├── processor.py            # Claude API → konu etiketi + sentiment
│   │   │   ├── embedder.py             # OpenAI text-embedding-3-small
│   │   │   ├── vector_store.py         # Qdrant upsert + search_examples()
│   │   │   ├── aggregator.py           # review_aggregates tablosunu günceller
│   │   │   ├── chat.py                 # Claude tool calling orkestrasyonu
│   │   │   ├── reporter.py             # Haftalık rapor metni üretimi
│   │   │   └── mailer.py               # SendGrid entegrasyonu
│   │   │
│   │   ├── jobs/
│   │   │   └── weekly_pipeline.py      # Cron: scrape→process→embed→store→aggregate
│   │   │
│   │   ├── models/                     # SQLAlchemy ORM modelleri
│   │   │   ├── review.py
│   │   │   ├── aggregate.py
│   │   │   └── task.py
│   │   │
│   │   └── schemas/                    # Pydantic request/response şemaları
│   │       ├── chat.py
│   │       ├── chart.py
│   │       └── task.py
│   │
│   ├── migrations/                     # Alembic DB migration'ları
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── tests/
│   │   ├── test_services/
│   │   └── test_api/
│   │
│   ├── alembic.ini
│   ├── pyproject.toml                  # Bağımlılıklar + tool config
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   ├── WeeklyTrendChart.tsx
│   │   │   │   ├── TopicDistributionChart.tsx
│   │   │   │   ├── SentimentTrendChart.tsx
│   │   │   │   └── IndustryComparisonChart.tsx
│   │   │   ├── chat/
│   │   │   │   ├── ChatPanel.tsx
│   │   │   │   ├── ChatMessage.tsx
│   │   │   │   └── AddToReportButton.tsx
│   │   │   ├── filters/
│   │   │   │   └── FilterPanel.tsx
│   │   │   └── layout/
│   │   │       └── DashboardLayout.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useChartData.ts         # /charts/* endpoint'lerini tüketir
│   │   │   └── useChat.ts              # chat state + streaming
│   │   │
│   │   ├── services/
│   │   │   └── api.ts                  # Axios instance + tüm API çağrıları
│   │   │
│   │   ├── types/
│   │   │   └── index.ts                # Review, ChartData, Message tipleri
│   │   │
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── package.json
│   └── vite.config.ts
│
├── Dockerfile                          # HF Spaces: React build + FastAPI serve
├── workflow-diagram.md
├── structure-diagram.md
├── .gitignore
└── .env.example
```


---

## KATMAN SORUMLULUKLARI

| Katman | Ne yapar | Ne yapmaz |
|--------|----------|-----------|
| `api/routes/` | HTTP parse, response döndür | İş mantığı |
| `services/` | İş mantığı, dış servis çağrıları | DB session almaz, HTTP bilmez |
| `models/` | ORM, tablo tanımı | Validation |
| `schemas/` | Request/response validation | DB operasyonu |
| `jobs/` | Pipeline orkestrasyonu | Kendi başına veri işleme |


---

## VERİ AKIŞI — HAFTALIK PIPELINE

```
weekly_pipeline.py (APScheduler — Her Pazartesi 09:00)
    │
    ├── scraper.py
    │     Apify'a istek at
    │     date > last_scraped_at filtresi
    │     Ham review listesi döner
    │
    ├── processor.py
    │     Her review için Claude API çağrısı
    │     → topics: ["veri kalitesi", "fiyat" ...]
    │     → sentiment: pozitif / negatif / nötr
    │     → summary: 1 cümlelik özet
    │
    ├── embedder.py
    │     Her review_text için OpenAI API çağrısı
    │     text-embedding-3-small → vector[1536]
    │
    ├── vector_store.py
    │     Qdrant'a upsert
    │     payload: text + embedding + metadata
    │
    ├── aggregator.py
    │     PostgreSQL reviews tablosuna INSERT
    │     review_aggregates tablosunu güncelle
    │     (week, topic, sentiment, industry, company_size, count)
    │
    └── reporter.py + mailer.py
          task_queue'daki bekleyen PM sorgularını çek
          Claude API ile haftalık raporu üret
          SendGrid ile email gönder
```


---

## VERİ AKIŞI — AI CHAT (TOOL CALLING)

```
POST /chat  {message: "Mart'tan sonra veri kalitesi şikayeti azaldı mı?"}
    │
    ▼
api/routes/chat.py          → services/chat.py'e iletir
    │
    ▼
services/chat.py
    Claude API'ya mesajı + tool tanımlarını gönderir
    │
    Claude soruyu analiz eder ve tool seçer:
    │
    ├── get_trend(topic, date_from, date_to, group_by)
    │       → PostgreSQL review_aggregates sorgusu
    │       → Haftalık COUNT verisi döner
    │
    └── search_examples(query, filters, top_k)
            → Qdrant semantik arama
            → En alakalı review örnekleri döner
    │
    Claude sonuçları birleştirip doğal dil cevap üretir
    │
    ▼
Response: {answer: "Evet, %23 azaldı. İşte detaylar..."}
```


---

## POSTGRESQL ŞEMA

```sql
-- Ham review'lar
CREATE TABLE reviews (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text          TEXT NOT NULL,
    rating        INT,
    date          DATE,
    industry      TEXT,
    company_size  TEXT,
    topics        TEXT[],
    sentiment     TEXT,
    created_at    TIMESTAMP DEFAULT now()
);

-- Grafik ve trend sorguları için önceden hesaplanmış aggregation
CREATE TABLE review_aggregates (
    week          DATE,        -- Pazartesi bazlı (date_trunc('week', date))
    topic         TEXT,
    sentiment     TEXT,
    industry      TEXT,
    company_size  TEXT,
    count         INT,
    PRIMARY KEY (week, topic, sentiment, industry, company_size)
);

-- PM'in "Rapora Ekle" butonundan oluşturduğu sorgular
CREATE TABLE task_queue (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt        TEXT NOT NULL,
    target_date   DATE NOT NULL,
    status        TEXT DEFAULT 'bekliyor',  -- bekliyor / tamamlandı
    result        TEXT,
    created_at    TIMESTAMP DEFAULT now()
);
```


---

## KÜTÜPHANELER

**Backend — `pyproject.toml`**

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "*"
uvicorn = "*"
sqlalchemy = "*"
alembic = "*"
asyncpg = "*"
qdrant-client = "*"
anthropic = "*"
openai = "*"
apscheduler = "*"
sendgrid = "*"
pydantic-settings = "*"
httpx = "*"
```

**Frontend — `package.json`**

```json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "recharts": "^2",
    "axios": "^1"
  },
  "devDependencies": {
    "typescript": "^5",
    "vite": "^5",
    "@types/react": "^18"
  }
}
```


---

## ÇEVRE DEĞİŞKENLERİ — `.env.example`

```env
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/review_radar

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=apollo_reviews

# AI
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Apify
APIFY_API_TOKEN=
APIFY_ACTOR_ID=

# SendGrid
SENDGRID_API_KEY=
REPORT_RECIPIENTS=pm@company.com,cpo@company.com

# App
ENVIRONMENT=development
```
