# CLAUDE.md — Review Radar

Apollo.io G2 review'larını analiz eden Product Intelligence sistemi. PM rolünü otomatize etmek için case study olarak geliştirildi.

## Proje Yapısı

```
review-radar/
├── backend/          # FastAPI — Python 3.11, uv ile yönetilir
└── frontend/         # React + Recharts + TypeScript
```

Detaylar için [`structure-diagram.md`](structure-diagram.md) ve [`workflow-diagram.md`](workflow-diagram.md).

## Backend Kuralları

### Katman Ayrımı — Kesinlikle Uyulacak

- `api/routes/` → sadece HTTP parse ve response. İş mantığı yok.
- `services/` → iş mantığı ve dış servis çağrıları. DB session almaz, HTTP bilmez.
- `models/` → SQLAlchemy ORM tanımları.
- `schemas/` → Pydantic request/response şemaları.
- `jobs/` → Pipeline orkestrasyonu. Kendi başına veri işleme yapmaz, service'leri çağırır.

### Servisler Birbirini Çağırmaz

Servisler arası bağımlılık `jobs/weekly_pipeline.py` üzerinden yürütülür. Bir service başka bir service'i import etmez.

### Paket Yönetimi

```bash
uv add <paket>      # paket ekle
uv run <komut>      # virtual env içinde çalıştır
uv sync             # bağımlılıkları yükle
```

Pip kullanma. Her şey `uv` üzerinden.

### Veritabanı

- Migration → Alembic. Şemayı direkt değiştirme.
- ORM → SQLAlchemy async. Raw SQL kullanma.
- `review_aggregates` tablosu her yeni review yazıldığında `aggregator.py` tarafından güncellenir.

### AI Servisleri

| Servis | Kullanım |
|--------|----------|
| `processor.py` | Claude API — konu etiketi + sentiment + özet |
| `embedder.py` | OpenAI text-embedding-3-small |
| `chat.py` | Claude API — tool calling (get_trend + search_examples) |
| `reporter.py` | Claude API — haftalık rapor metni |

### Tool Calling Mimarisi

`services/chat.py` iki tool tanımlar:
- `get_trend(topic, date_from, date_to, group_by)` → PostgreSQL `review_aggregates`
- `search_examples(query, filters, top_k)` → Qdrant semantik arama

Claude hangi tool'u çağıracağına kendisi karar verir.

## Frontend Kuralları

- Tüm API çağrıları `services/api.ts` içinde. Component'lar URL bilmez.
- Hook'lar (`useChartData`, `useChat`) state yönetimini üstlenir.
- Component'lar sadece render eder.

## Çevre Değişkenleri

`.env.example` şablonu `backend/` içinde. Gerçek `.env` asla commit edilmez.

## Deploy

Hugging Face Spaces — Docker. React build output FastAPI tarafından serve edilir.
