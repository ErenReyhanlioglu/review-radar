# Review Radar — Terminal Komutları

## Günlük Başlangıç (her oturumda)

```bash
# 1. Docker container'ları başlat (Docker Desktop açık olmalı)
docker start postgres qdrant

# 2. Backend dev server
cd backend
uv run uvicorn app.main:app --reload --port 8001

# 3. Frontend dev server (ayrı terminalde)
cd frontend
npm run dev
```

> Backend: `http://localhost:8001` · Frontend: `http://localhost:5173`

---

## Simülasyon (API)

```bash
# Mevcut simüle tarih ve pipeline durumu
curl http://localhost:8001/simulation/status

# Bir ay ilerlet — loader 0 yeni review bulur, sadece reporter çalışır (~15-30s)
curl -X POST http://localhost:8001/simulation/advance

# Başa sar (2025-07-01) — VERİYİ SİLMEZ, sadece simulated_date'i sıfırlar
curl -X POST http://localhost:8001/simulation/reset
```

---

## Script'ler

```bash
cd backend

# Tüm ayları sırayla işle (ilk kurulumda bir kez çalıştır)
uv run python -c "import sys; sys.path.insert(0,'.'); exec(open('scripts/advance_all.py').read())"

# Veri bütünlüğü kontrolü (reviews, aggregates, reports, Qdrant)
uv run python -c "import sys; sys.path.insert(0,'.'); exec(open('scripts/check_data.py').read())"
```

---

## API Endpoint'leri

```bash
# Charts
curl http://localhost:8001/charts/trend
curl http://localhost:8001/charts/topics
curl http://localhost:8001/charts/sentiment
curl "http://localhost:8001/charts/trend?topic=fiyat&sentiment=negatif"

# Chat (AI soru-cevap + chart_data)
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hangi konu en fazla sikayet aliyor?\"}"

# Tasks (rapora ekle)
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Enterprise musterilerin sikayetleri?\", \"target_date\": \"2025-08-01\"}"
curl http://localhost:8001/tasks

# Reports
curl http://localhost:8001/reports/latest
curl http://localhost:8001/reports/2025-07-01

# Health
curl http://localhost:8001/health
```

---

## Veritabanı Kontrol

```bash
cd backend

# Hızlı kontrol — tüm tablolar
uv run python -c "
import asyncio
from sqlalchemy import text
from app.api.deps import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        for t in ['reviews', 'review_aggregates', 'task_queue', 'system_config', 'reports']:
            r = await db.execute(text(f'SELECT COUNT(*) FROM {t}'))
            print(f'{t}: {r.scalar()}')

asyncio.run(check())
"

# Qdrant point sayısı
uv run python -c "
import asyncio
from app.services.vector_store import _get_client
from app.config import settings

async def check():
    c = _get_client()
    info = await c.get_collection(settings.qdrant_collection)
    print('Qdrant points:', info.points_count)
    await c.close()

asyncio.run(check())
"
```

---

## Docker (PostgreSQL + Qdrant)

```bash
# İlk kurulumda oluştur
docker run -d --name postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=review_radar -p 5432:5432 postgres:16
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# Günlük başlat / durdur
docker start postgres qdrant
docker stop  postgres qdrant

# Logları izle
docker logs postgres
docker logs qdrant

# Qdrant dashboard → http://localhost:6333/dashboard
```

---

## Alembic (DB Migration)

```bash
cd backend

uv run alembic upgrade head          # son migration'ı uygula
uv run alembic downgrade -1          # bir adım geri al
uv run alembic current               # hangi revision'dasın
uv run alembic history               # tüm migration geçmişi

# Model değiştiğinde yeni migration (PostgreSQL çalışıyor olmalı)
uv run alembic revision --autogenerate -m "açıklama"
```

---

## Backend

```bash
cd backend

uv sync                              # bağımlılıkları yükle
uv add <paket>                       # yeni paket ekle
uv add --dev <paket>                 # sadece dev ortamına ekle
```

---

## Frontend

```bash
cd frontend

npm install          # bağımlılıkları yükle (ilk kurulum)
npm run dev          # dev server başlat (port 5173)
npm run build        # production build
```

---

## Jupyter (Notebook)

```bash
cd backend
uv run jupyter notebook ../notebooks/
```

| Notebook | İçerik |
|----------|--------|
| `01_explore_raw_data.ipynb` | Ham veri keşfi ve temizleme |
| `02_enriched_data_explore.ipynb` | Claude enrichment sonuçları |

---

## Test & Debug

```bash
cd backend

# Import zincirleri sağlıklı mı?
uv run python -c "from app.main import app; print('OK, routes:', len(app.routes))"
uv run python -c "from app.jobs.monthly_pipeline import run_pipeline; print('Pipeline OK')"

# Config değerleri
uv run python -c "from app.config import settings; print({k: '***' if 'key' in k else v for k,v in settings.model_dump().items()})"
```

---

## Git

```bash
git status
git add -p                 # değişiklikleri parça parça incele
git commit -m "mesaj"
git log --oneline -10
```

---

## Deploy (Hugging Face Spaces)

```bash
docker build -t review-radar .
docker run -p 7860:7860 --env-file backend/.env review-radar
```
