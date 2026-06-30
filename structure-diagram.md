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
│   │   │       ├── tasks.py            # POST /tasks, GET /tasks
│   │   │       ├── reports.py          # GET /reports, /reports/latest, /reports/{month}
│   │   │       └── simulation.py       # POST /simulation/advance, GET /simulation/status
│   │   │
│   │   ├── services/                   # İş mantığı — route'lardan bağımsız
│   │   │   ├── loader.py               # reviews_clean.json'dan tarih aralığı filtreli okuma
│   │   │   ├── processor.py            # Claude API → konu etiketi + sentiment + özet
│   │   │   ├── embedder.py             # OpenAI text-embedding-3-small
│   │   │   ├── vector_store.py         # Qdrant upsert + search_examples()
│   │   │   ├── aggregator.py           # review_aggregates tablosunu günceller
│   │   │   ├── chat.py                 # Claude tool calling orkestrasyonu
│   │   │   ├── reporter.py             # Aylık rapor metni üretimi
│   │   │   └── mailer.py               # SendGrid entegrasyonu
│   │   │
│   │   ├── jobs/
│   │   │   └── monthly_pipeline.py     # Simülasyon tetiklemeli pipeline orkestrasyonu
│   │   │
│   │   ├── models/                     # SQLAlchemy ORM modelleri
│   │   │   ├── review.py
│   │   │   ├── aggregate.py
│   │   │   ├── task.py
│   │   │   ├── report.py               # reports tablosu
│   │   │   └── config.py               # system_config tablosu
│   │   │
│   │   └── schemas/                    # Pydantic request/response şemaları
│   │       ├── chat.py
│   │       ├── chart.py
│   │       ├── task.py
│   │       └── simulation.py           # SimulationStatus, AdvanceResponse
│   │
│   ├── data/
│   │   ├── raw/                        # Ham Apify JSON'ları (git'e girmez)
│   │   └── reviews_clean.json          # 770 temiz Apollo.io review'ı (git'e girmez)
│   │
│   ├── migrations/                     # Alembic DB migration'ları
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── scripts/                        # Tek seferlik yardımcı scriptler
│   │   ├── advance_all.py              # Tüm ayları sırayla ilerletir
│   │   ├── check_data.py               # JSON veri setini kontrol eder
│   │   └── generate_missing_reports.py # Eksik raporları doldurur
│   │
│   ├── tests/
│   │   ├── test_services/
│   │   └── test_api/
│   │
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   ├── MonthlyTrendChart.tsx
│   │   │   │   ├── TopicDistributionChart.tsx
│   │   │   │   ├── SentimentTrendChart.tsx
│   │   │   │   └── CompanySizeChart.tsx
│   │   │   ├── chat/
│   │   │   │   ├── ChatPanel.tsx
│   │   │   │   ├── ChatMessage.tsx
│   │   │   │   └── AddToReportButton.tsx
│   │   │   ├── simulation/
│   │   │   │   └── SimulationBar.tsx   # Simüle tarih + "→ Sonraki Ay" butonu
│   │   │   ├── filters/
│   │   │   │   └── FilterPanel.tsx
│   │   │   └── layout/
│   │   │       └── DashboardLayout.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useChartData.ts         # /charts/* endpoint'lerini tüketir
│   │   │   ├── useChat.ts              # chat state + streaming
│   │   │   └── useSimulation.ts        # simüle tarih state + advance tetikleme
│   │   │
│   │   ├── services/
│   │   │   └── api.ts                  # Axios instance + tüm API çağrıları
│   │   │
│   │   ├── types/
│   │   │   └── index.ts                # Review, ChartData, Message, SimulationStatus tipleri
│   │   │
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── package.json
│   └── vite.config.ts
│
├── notebooks/
│   └── 01_explore_raw_data.ipynb       # Veri keşfi + temizleme
│
├── Dockerfile                          # HF Spaces: React build + FastAPI serve
├── workflow-diagram.md
├── structure-diagram.md
├── CLAUDE.md
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

## VERİ AKIŞI — SİMÜLASYON PIPELINE

```
POST /simulation/advance
    │
    ▼
monthly_pipeline.py  ← job orchestrator
    │
    ├── loader.py
    │     reviews_clean.json'ı oku
    │     date BETWEEN (simulated_date - 1 ay) AND simulated_date filtrele
    │     reviews tablosundaki review_id'lerle karşılaştır
    │     → sadece işlenmemiş review'ları döndür
    │
    ├── processor.py
    │     Her review için Claude API çağrısı
    │     → topics: ["veri kalitesi", "fiyat", "UX" ...]
    │     → sentiment: pozitif / negatif / nötr
    │     → summary: 1 cümlelik özet
    │
    ├── embedder.py
    │     likes + dislikes metni birleştir
    │     OpenAI API → vector[1536]
    │
    ├── vector_store.py
    │     Qdrant'a upsert
    │     payload: text + embedding + metadata
    │
    ├── aggregator.py
    │     PostgreSQL reviews tablosuna INSERT
    │     review_aggregates tablosunu güncelle
    │     (month, topic, sentiment, company_size, count)
    │
    ├── system_config güncelle
    │     simulated_date += 1 ay
    │
    ├── reporter.py
    │     Claude API ile aylık raporu üret (standart bölümler)
    │     NOT: PM notları (pm_sections) rapor metnine dahil değil;
    │     GET /reports/{month} ile ayrıca döner
    │
    └── mailer.py
          SendGrid ile raporu email gönder
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
    ├── get_trend(topic, date_from, date_to, sentiment, company_size, rating_min/max, visualize, chart_title)
    │       → PostgreSQL reviews tablosu sorgusu
    │       → Aylık avg_rating + count döner
    │
    ├── get_breakdown(group_by, topic, sentiment, company_size, date_from/to, rating_min/max, visualize, chart_title)
    │       → PostgreSQL reviews tablosu sorgusu
    │       → group_by: topic / sentiment / company_size
    │       → Her segment için count + avg_rating döner
    │
    ├── search_examples(query, topic, sentiment, company_size, top_k, date_from/to, rating_min/max, visualize, chart_title)
    │       → Qdrant semantik arama
    │       → En alakalı review örnekleri döner
    │
    ├── list_reports()
    │       → reports tablosundaki tüm ayların listesi
    │
    ├── get_report(month)
    │       → Belirtilen aya ait reporter.py çıktısı (markdown)
    │
    └── get_report_notes(month)
            → PM'in o aya "Rapora Ekle" ile kaydettiği soru-cevap çiftleri
            → task_queue tablosundan (status=tamamlandı)
    │
    Claude sonuçları birleştirip doğal dil cevap üretir
    │
    ▼
Response: {
  answer: "Evet, %23 azaldı. İşte detaylar...",
  charts: [
    { type: "trend", data: [{month, avg_rating, count}] },
    { type: "breakdown", group_by: "topic", data: [{group_value, count, avg_rating}] },
    { type: "examples", data: [{date, rating, company_size, topics, sentiment, summary}] }
  ]
}
```


---

## POSTGRESQL ŞEMA

```sql
-- Ham + zenginleştirilmiş review'lar
CREATE TABLE reviews (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id     TEXT UNIQUE NOT NULL,   -- duplicate koruması
    likes         TEXT,
    dislikes      TEXT,
    rating        FLOAT,
    date          DATE,
    company_size  TEXT,
    topics        TEXT[],
    sentiment     TEXT,
    summary       TEXT,
    created_at    TIMESTAMP DEFAULT now()
);

-- Grafik ve trend sorguları için pre-computed aggregation
CREATE TABLE review_aggregates (
    month         DATE,
    topic         TEXT,
    sentiment     TEXT,
    company_size  TEXT,
    count         INT,
    PRIMARY KEY (month, topic, sentiment, company_size)
);

-- PM'in "Rapora Ekle" ile kaydettiği soru-cevap çiftleri
CREATE TABLE task_queue (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt        TEXT NOT NULL,
    target_date   DATE NOT NULL,
    status        TEXT DEFAULT 'tamamlandı',  -- anında tamamlandı olarak kaydedilir
    result        TEXT,                       -- AI'ın verdiği cevap
    chart_data    JSONB,                      -- varsa grafik verisi
    created_at    TIMESTAMP DEFAULT now()
);

-- Aylık markdown raporları
CREATE TABLE reports (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    month      DATE UNIQUE NOT NULL,  -- ayın 1'i: 2025-08-01
    content    TEXT NOT NULL,         -- Claude'un ürettiği markdown
    created_at TIMESTAMP DEFAULT now()
);

-- PoC simülasyon durumu
CREATE TABLE system_config (
    key   TEXT PRIMARY KEY,
    value TEXT
);
-- Anahtarlar:
-- simulated_date    başlangıç: '2025-07-01'
-- pipeline_running  'true' / 'false'  (zaten çalışıyor kontrolü için kritik)
-- pipeline_last_run NULL  (kod tarafından set edilmiyor, hep null döner)
```


---

## API ENDPOINT'LERİ

| Method | Path | Açıklama |
|--------|------|----------|
| `POST` | `/simulation/advance` | Simüle tarihi 1 ay ilerlet, pipeline'ı tetikle |
| `GET`  | `/simulation/status` | Mevcut simüle tarih + son çalışma bilgisi |
| `POST` | `/simulation/reset` | Başa sar |
| `GET`  | `/charts/trend` | Aylık puan trendi |
| `GET`  | `/charts/topics` | Konu dağılımı |
| `GET`  | `/charts/sentiment` | Sentiment trendi |
| `GET`  | `/charts/company-size` | Şirket büyüklüğü dağılımı |
| `POST` | `/chat` | AI chat mesajı gönder |
| `POST` | `/tasks` | Task queue'ya doğrudan yaz (opsiyonel) |
| `GET`  | `/tasks` | Task listesini getir |
| `GET`  | `/reports` | Tüm aylık raporları listele (desc sıra) |
| `GET`  | `/reports/latest` | En son raporu getir (pm_sections dahil) |
| `GET`  | `/reports/{month}` | Belirli aya ait raporu getir (pm_sections dahil) |
| `POST` | `/reports/{month}/append` | Chat'teki analizi o ayın raporuna ekle (pm_sections) |
| `POST` | `/reports/{month}/send` | Raporu belirtilen e-posta adreslerine gönder |


---

## KÜTÜPHANELER

**Backend — `pyproject.toml`**

```toml
[project]
dependencies = [
  "fastapi",
  "uvicorn",
  "sqlalchemy",
  "alembic",
  "asyncpg",
  "qdrant-client",
  "anthropic",
  "openai",
  "sendgrid",
  "pydantic-settings",
  "httpx",
]
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

# SendGrid
SENDGRID_API_KEY=
REPORT_RECIPIENTS=pm@company.com

# App
ENVIRONMENT=development
```
