# Apollo.io Product Review Intelligence System
## Sistem Mimarisi & Akış Diyagramı

---

## GENEL AKIŞ

```
┌─────────────────────────────────────────────────────────────┐
│                    HAFTALIK CRON JOB                        │
│                   Her Pazartesi 09:00                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│           APIFY — G2 SCRAPER            │
│                                         │
│  Mod: Incremental (sadece yeni review)  │
│  Filtre: date > last_scraped_at         │
│                                         │
│  Çekilen alanlar:                       │
│  • review_text                          │
│  • rating (1-5)                         │
│  • date                                 │
│  • reviewer_industry                    │
│  • reviewer_company_size                │
│  • likes (ayrı metin)                   │
│  • dislikes (ayrı metin)                │
└─────────────────────┬───────────────────┘
                      │
                      │  Ham review'lar
                      ▼
┌─────────────────────────────────────────┐
│         VERİ İŞLEME — CLAUDE API        │
│                                         │
│  Her review için:                       │
│  • Konu etiketi                         │
│    ["veri kalitesi", "fiyat", "UX"...]  │
│  • Duygu skoru                          │
│    pozitif / negatif / nötr             │
│  • 1 cümlelik özet                      │
└──────────┬──────────────────────────────┘
           │
           │  Zenginleştirilmiş review'lar
           ▼
┌─────────────────────────────────────────┐
│        OPENAI — EMBEDDING               │
│        (text-embedding-3-small)         │
│                                         │
│  review_text → vector[1536]             │
└──────────┬──────────────────────────────┘
           │
           │  Vector + metadata
           ├──────────────────────────────────────────┐
           │                                          │
           ▼                                          ▼
┌──────────────────────────┐         ┌────────────────────────────────┐
│    QDRANT VECTOR STORE   │         │           POSTGRESQL           │
│    (semantik arama)      │         │                                │
│                          │         │  reviews tablosu               │
│  {                       │         │  • id, text, rating, date      │
│    text: "bounce rate…", │         │  • industry, company_size      │
│    embedding: [...],     │         │  • topics[], sentiment         │
│    metadata: {           │         │                                │
│      date, rating,       │         │  review_aggregates tablosu     │
│      industry,           │         │  • week, topic, sentiment      │
│      company_size,       │         │  • industry, company_size      │
│      topics[],           │         │  • count (grafik & trend kaynağı)│
│      sentiment           │         │                                │
│    }                     │         │  task_queue tablosu            │
│  }                       │         │  • prompt, target_date         │
│                          │         │  • status: bekliyor/tamamlandı │
└──────────────────────────┘         └────────────────────────────────┘
           │                                          │
           └──────────────────┬───────────────────────┘
                              │
                 ┌────────────┴──────────────┐
                 │                           │
                 ▼                           ▼
  ┌──────────────────────┐    ┌─────────────────────────────┐
  │  DASHBOARD GRAFİKLERİ│    │    OTOMATİK HAFTALIK RAPOR  │
  │  (PostgreSQL'den)    │    │                             │
  │                      │    │  Standart bölümler:         │
  │  • Haftalık puan     │    │  • Top 5 şikayet            │
  │    trendi            │    │  • Geçen haftaya göre       │
  │  • Konu dağılımı     │    │    değişim                  │
  │  • Sentiment trendi  │    │  • Puan trendi              │
  │  • Sektör bazlı      │    │  • Sektör dağılımı          │
  │    karşılaştırma     │    │  + Task queue'daki          │
  └──────────────────────┘    │    PM sorguları             │
                              └──────────────┬──────────────┘
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │      CLAUDE API      │
                                  │                      │
                                  │  • Standart raporu   │
                                  │    üret              │
                                  │  • Task'ları         │
                                  │    çalıştır          │
                                  │  • Sonuçları rapora  │
                                  │    ekle              │
                                  └──────────┬───────────┘
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │       SENDGRID       │
                                  │                      │
                                  │  Raporu ilgili       │
                                  │  kişilere email      │
                                  └──────────────────────┘
```


---

## KULLANICI DASHBOARD AKIŞI

```
PM dashboard'a giriyor
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│                                                            │
│    SOL PANEL                        SAĞ PANEL              │
│    (Grafikler)                      (AI Chat)              │
│                                                            │
│  ┌─────────────────────┐        ┌───────────────────────┐  │
│  │ • Haftalık puan     │        │ Kullanıcı:            │  │
│  │   trendi (çizgi)    │        │ "Mart'tan sonra veri  │  │
│  │                     │        │  kalitesi şikayeti    │  │
│  │ • Konu dağılımı     │        │  azaldı mı?"          │  │
│  │   (pasta grafik)    │        │                       │  │
│  │                     │        │ AI (tool calling):    │  │
│  │ • Sentiment trendi  │        │  → get_trend()        │  │
│  │   (çizgi grafik)    │        │    PostgreSQL'e gider │  │
│  │                     │        │  → search_examples()  │  │
│  │ • Sektör bazlı      │        │    Qdrant'a gider     │  │
│  │   karşılaştırma     │        │                       │  │
│  │   (bar grafik)      │        │ "Evet, %23 azaldı.    │  │
│  │                     │        │  İşte detaylar..."    │  │
│  │ Filtreler:          │        │                       │  │
│  │ • Tarih aralığı     │        │ ─────────────────     │  │
│  │ • Sektör            │        │                       │  │
│  │ • Şirket büyüklüğü  │        │ [ Rapora Ekle ▼ ]     │  │
│  │ • Konu              │        │   → Bu Pazartesi      │  │
│  │ • Puan              │        │   → Gelecek Pazartesi │  │
│  └─────────────────────┘        └───────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
         │
         │  PM ilginç bir şey görüyor
         │  AI'a soruyor
         │  Cevabı beğeniyor
         │  "Rapora Ekle" butonuna basıyor
         ▼
┌─────────────────────────┐
│  POSTGRESQL TASK QUEUE  │
│                         │
│  status: "bekliyor"     │
│  target: "2026-07-07"   │
└───────────┬─────────────┘
            │
            │  Hedef Pazartesi gelince
            ▼
┌─────────────────────────┐
│    RAPORA EKLENİR       │
│    status: "tamamlandı" │
└─────────────────────────┘
```


---

## AI CHAT — TOOL CALLING MİMARİSİ

```
PM soruyor: "Mart'tan sonra veri kalitesi şikayeti azaldı mı?"
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE API                               │
│                (Tool Calling modu)                          │
│                                                             │
│  Soruyu analiz eder:                                        │
│  • Analitik mi? (trend, sayı, karşılaştırma)               │
│  • Semantik mi? (örnek bul, benzer review'lar)             │
│  • İkisi birden mi?                                         │
└──────────────┬──────────────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌─────────────┐   ┌──────────────────────────────────┐
│ get_trend() │   │         search_examples()         │
│             │   │                                   │
│ Parametreler│   │  Parametreler:                    │
│ • topic     │   │  • query (doğal dil)              │
│ • date_from │   │  • filters: {topic, date,         │
│ • date_to   │   │    sentiment, industry}           │
│ • group_by  │   │  • top_k                          │
│   (week/    │   │                                   │
│    month)   │   │  Qdrant'a gider                   │
│             │   │  Semantik benzerlik + metadata    │
│ PostgreSQL  │   │  filtresi                         │
│ aggregates  │   └──────────────┬───────────────────┘
│ tablosuna   │                  │
│ gider       │                  │
└──────┬──────┘                  │
       │                         │
       └────────────┬────────────┘
                    │
                    ▼
          ┌──────────────────┐
          │   CLAUDE API     │
          │                  │
          │ Sonuçları        │
          │ birleştirip      │
          │ doğal dil cevap  │
          │ üretir           │
          └──────────────────┘
```


---

## POSTGRESQL ŞEMA

```
reviews
────────────────────────────────────
id            UUID  PK
text          TEXT
rating        INT
date          DATE
industry      TEXT
company_size  TEXT
topics        TEXT[]
sentiment     TEXT
created_at    TIMESTAMP

review_aggregates
────────────────────────────────────
week          DATE   (Pazartesi bazlı)
topic         TEXT
sentiment     TEXT
industry      TEXT
company_size  TEXT
count         INT
PK: (week, topic, sentiment, industry, company_size)

task_queue
────────────────────────────────────
id            UUID  PK
prompt        TEXT
target_date   DATE
status        TEXT   (bekliyor / tamamlandı)
result        TEXT
created_at    TIMESTAMP
```


---

## TECH STACK

| Katman        | Teknoloji                           |
|---------------|-------------------------------------|
| Scraping      | Apify — G2 Scraper (incremental)    |
| Embedding     | OpenAI text-embedding-3-small       |
| Vector Store  | Qdrant (semantik arama)             |
| AI            | Claude API — sonnet-4-6             |
| Backend       | FastAPI                             |
| Frontend      | React + Recharts                    |
| Veritabanı    | PostgreSQL (aggregates + task queue)|
| Email         | SendGrid                            |
| Zamanlayıcı   | APScheduler (cron job)              |
| Deploy        | Hugging Face Spaces                 |


---

## ZAMAN TAHMİNİ

| Görev                                         | Süre        |
|-----------------------------------------------|-------------|
| Apify scraper + incremental logic             | 2 saat      |
| Claude API veri işleme + OpenAI embedding     | 2 saat      |
| Qdrant entegrasyonu                           | 1 saat      |
| PostgreSQL şema + aggregation yazma           | 2 saat      |
| FastAPI backend                               | 3 saat      |
| Claude API tool calling (get_trend + search)  | 2 saat      |
| Task queue (PostgreSQL)                       | 1 saat      |
| React frontend + grafikler                    | 4 saat      |
| Email rapor (SendGrid)                        | 2 saat      |
| Cron job + deploy                             | 2 saat      |
| Test + debug                                  | 3 saat      |
| **TOPLAM**                                    | **24 saat** |


---

## TAKVİM

| Gün        | Yapılacak                                              |
|------------|--------------------------------------------------------|
| 29 Haziran | Scraper + Claude işleme + OpenAI embedding + Qdrant + PostgreSQL şema |
| 30 Haziran | FastAPI backend + tool calling + React frontend + grafikler |
| 1 Temmuz   | Chat UI + Task Queue + Email rapor + Cron job + Deploy |
| 2-3 Temmuz | Buffer + Rapor yazımı + Teslim                         |
