# CLAUDE.md — Review Radar

Apollo.io G2 review'larını analiz eden Product Intelligence sistemi. PM rolünü otomatize etmek için case study olarak geliştirildi.

## Proje Yapısı

```
review-radar/
├── backend/          # FastAPI — Python 3.11, uv ile yönetilir
├── frontend/         # React + Recharts + TypeScript
└── notebooks/        # Veri keşfi (Jupyter)
```

Referans dokümanlar:
- [`workflow-diagram.md`](workflow-diagram.md) — Sistem akışı
- [`structure-diagram.md`](structure-diagram.md) — Klasör ve kod yapısı
- [`dataset-diagram.md`](dataset-diagram.md) — Veri seti şeması ve alan detayları

## Veri Seti

- **Kaynak:** `backend/data/reviews_clean.json` — 770 unique Apollo.io review
- **Tarih aralığı:** Temmuz 2025 → Haziran 2026
- **Git'e girmez:** `backend/data/` `.gitignore`'da

## PoC Simülasyon Mimarisi

Bu bir PoC projesidir. Gerçek cron job / Apify scraping yerine simülasyon kullanılır:

- `POST /simulation/advance` → simüle tarihi 1 ay ileri sar, pipeline'ı tetikle
- `GET /simulation/status` → mevcut simüle tarih
- `POST /simulation/reset` → başa sar
- Simülasyon durumu PostgreSQL `system_config` tablosunda tutulur
- `loader.py` her çağrıda `reviews_clean.json`'dan o ayın review'larını filtreler

## Backend Kuralları

### Katman Ayrımı — Kesinlikle Uyulacak

- `api/routes/` → sadece HTTP parse ve response. İş mantığı yok.
- `services/` → iş mantığı ve dış servis çağrıları. DB session almaz, HTTP bilmez.
- `models/` → SQLAlchemy ORM tanımları.
- `schemas/` → Pydantic request/response şemaları.
- `jobs/` → Pipeline orkestrasyonu. Kendi başına veri işleme yapmaz, service'leri çağırır.

### Servisler Birbirini Çağırmaz

Servisler arası bağımlılık `jobs/monthly_pipeline.py` üzerinden yürütülür. Bir service başka bir service'i import etmez.

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
- `industry` alanı kullanılmaz — veri setinde %86 null.

### PostgreSQL Tabloları

| Tablo | Amaç |
|-------|------|
| `reviews` | Claude ile zenginleştirilmiş review'lar |
| `review_aggregates` | Grafik & trend sorguları için pre-computed aggregation |
| `task_queue` | PM'in "Rapora Ekle" ile kaydettiği soru-cevap çiftleri (pm_sections) |
| `system_config` | Simülasyon durumu (simulated_date vb.) |

### AI Servisleri

| Servis | Kullanım |
|--------|----------|
| `loader.py` | reviews_clean.json'dan tarih filtreli okuma |
| `processor.py` | Claude API — konu etiketi + sentiment + özet |
| `embedder.py` | OpenAI text-embedding-3-small |
| `vector_store.py` | Qdrant upsert + search_examples() |
| `aggregator.py` | review_aggregates tablosunu günceller |
| `chat.py` | Claude API — tool calling |
| `reporter.py` | Claude API — aylık rapor metni |
| `mailer.py` | SendGrid entegrasyonu |

### Tool Calling Mimarisi

`services/chat.py` altı tool tanımlar:
- `get_trend(topic, date_from, date_to, sentiment, company_size, rating_min, rating_max, visualize, chart_title)` → PostgreSQL `reviews` tablosu, aylık trend
- `get_breakdown(group_by, topic, sentiment, company_size, date_from, date_to, rating_min, rating_max, visualize, chart_title)` → PostgreSQL `reviews` tablosu, boyuta göre kırılım
- `search_examples(query, topic, sentiment, company_size, top_k, date_from, date_to, rating_min, rating_max, visualize, chart_title)` → Qdrant semantik arama
- `list_reports()` → Üretilmiş aylık raporların listesi (`reports` tablosu)
- `get_report(month)` → Belirli aya ait rapor metnini getirir
- `get_report_notes(month)` → PM'in o aya "Rapora Ekle" ile kaydettiği analizler (`task_queue`)

`industry` filtresi yoktur — sadece `topic`, `date`, `sentiment`, `company_size`, `rating_min/max`.

`visualize` parametresiyle Claude hangi tool çıktısının grafik olarak gösterileceğine kendisi karar verir; yanıt başına maksimum 2 grafik.

Claude hangi tool'u çağıracağına kendisi karar verir.

### Konu Etiket Listesi (processor.py)

Claude'a verilecek sabit etiket listesi:
`veri kalitesi`, `fiyat`, `email deliverability`, `UX / kullanım kolaylığı`,
`müşteri desteği`, `entegrasyon`, `arama & filtreleme`, `otomasyon`,
`raporlama & analitik`, `genel olumlu`

## Frontend Kuralları

- Tüm API çağrıları `services/api.ts` içinde. Component'lar URL bilmez.
- Hook'lar (`useChartData`, `useChat`, `useSimulation`) state yönetimini üstlenir.
- Component'lar sadece render eder.
- `industry` filtresi yoktur — sadece `company_size`, `topic`, `tarih aralığı`, `puan`.

## Çevre Değişkenleri

`.env.example` şablonu `backend/` içinde. Gerçek `.env` asla commit edilmez.

## Deploy

Hugging Face Spaces — Docker. React build output FastAPI tarafından serve edilir.
