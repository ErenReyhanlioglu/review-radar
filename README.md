# Review Radar

Apollo.io ürün departmanı için G2 review'larını analiz eden, aylık raporlar üreten ve PM'lere AI destekli insight sunan bir Product Intelligence sistemi. PM rolünü otomatize etmek için geliştirilmiş bir case study PoC'udur.

## Özellikler

- **Simüle aylık pipeline** — "Sonraki Ay" butonuyla zaman ilerletilir, sistem o ayın review'larını ilk kez görüyormuş gibi işler
- **AI analizi** — Claude API ile konu etiketleme, sentiment analizi ve özetleme
- **Semantik arama** — Qdrant vector store üzerinde doğal dil sorguları
- **Trend analizi** — PostgreSQL aggregation tabloları ile aylık trend grafikler
- **AI chat** — Tool calling ile PM'lerin analitik sorularını anlık yanıtlama
- **Aylık rapor** — PM sorgularını birleştirerek SendGrid ile otomatik email

## Veri Seti

G2'den çekilmiş 770 unique Apollo.io review'ı (Temmuz 2025 – Haziran 2026).

## Tech Stack

| Katman | Teknoloji |
|--------|-----------|
| Veri Kaynağı | Local JSON (770 review, önceden çekildi) |
| Embedding | OpenAI text-embedding-3-small |
| Vector Store | Qdrant |
| AI | Claude API — claude-sonnet-4-6 |
| Backend | FastAPI |
| Frontend | React + Recharts |
| Veritabanı | PostgreSQL |
| Email | SendGrid |
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

## Mimari & Dokümantasyon

| Dosya | İçerik |
|-------|--------|
| [`workflow-diagram.md`](workflow-diagram.md) | Sistem akışı ve veri pipeline'ı |
| [`structure-diagram.md`](structure-diagram.md) | Klasör, kod yapısı ve API endpoint'leri |
| [`dataset-diagram.md`](dataset-diagram.md) | Veri seti şeması, alan detayları, tablo ilişkileri |

## Lisans

MIT
