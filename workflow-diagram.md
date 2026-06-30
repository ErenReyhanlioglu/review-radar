# Apollo.io Product Review Intelligence System
## Sistem Mimarisi & Akış Diyagramı

---

## GENEL AKIŞ

```
┌─────────────────────────────────────────────────────────────┐
│              SİMÜLASYON KONTROLÜ (PoC)                      │
│                                                             │
│  PM "→ Sonraki Ay" butonuna basar                           │
│  simulated_date: 2025-08-01                                 │
│  POST /simulation/advance                                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│           JSON LOADER                   │
│                                         │
│  Kaynak: backend/data/reviews_clean.json│
│  Filtre: date BETWEEN                   │
│    simulated_date - 1 ay                │
│    AND simulated_date                   │
│                                         │
│  Alanlar:                               │
│  • reviewId (duplicate koruması)        │
│  • starRating                           │
│  • date                                 │
│  • company_size                         │
│  • likes                                │
│  • dislikes                             │
└─────────────────────┬───────────────────┘
                      │
                      │  O ayın review'ları
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
│  likes + dislikes → vector[1536]        │
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
│  {                       │         │  • reviewId, likes, dislikes   │
│    text: "bounce rate…", │         │  • rating, date, company_size  │
│    embedding: [...],     │         │  • topics[], sentiment, summary│
│    metadata: {           │         │                                │
│      date, rating,       │         │  review_aggregates tablosu     │
│      company_size,       │         │  • month, topic, sentiment     │
│      topics[],           │         │  • company_size, count         │
│      sentiment           │         │    (grafik & trend kaynağı)    │
│    }                     │         │                                │
│  }                       │         │  task_queue tablosu            │
│                          │         │  • prompt, target_date         │
│                          │         │  • status: bekliyor/tamamlandı │
│                          │         │                                │
│                          │         │  system_config tablosu         │
│                          │         │  • simulated_date              │
│                          │         │  • pipeline_running            │
│                          │         │  • pipeline_last_run           │
│                          │         │                                │
│                          │         │  reports tablosu               │
│                          │         │  • month (UNIQUE), content     │
│                          │         │    (markdown rapor metni)      │
└──────────────────────────┘         └────────────────────────────────┘
           │                                          │
           └──────────────────┬───────────────────────┘
                              │
                 ┌────────────┴──────────────┐
                 │                           │
                 ▼                           ▼
  ┌──────────────────────┐    ┌─────────────────────────────┐
  │  DASHBOARD GRAFİKLERİ│    │    OTOMATİK AYLIK RAPOR      │
  │  (PostgreSQL'den)    │    │                             │
  │                      │    │  Standart bölümler:         │
  │  • Aylık puan        │    │  • Top 5 şikayet            │
  │    trendi            │    │  • Geçen aya göre           │
  │  • Konu dağılımı     │    │    değişim                  │
  │  • Sentiment trendi  │    │  • Puan trendi              │
  │  • Şirket büyüklüğü  │    │  • Şirket büyüklüğü dağ.   │
  │    karşılaştırması   │    │                             │
  └──────────────────────┘    │  + pm_sections (ayrı alan) │
                              │    PM'in "Rapora Ekle" ile  │
                              │    kaydettiği analizler     │
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

## SİMÜLASYON KONTROLÜ AKIŞI

```
┌──────────────────────────────────────────────────────────┐
│                  DASHBOARD — ÜST BAR                     │
│                                                          │
│  Simüle Tarih: Ekim 2025                                 │
│                                                          │
│  [ ← Önceki Ay ]       [ → Sonraki Ay ]                  │
│                         [ ↺ Sıfırla ]                    │
└──────────────────┬───────────────────────────────────────┘
                   │
                   │  POST /simulation/advance
                   ▼
┌──────────────────────────────────────────────────────────┐
│              BACKEND — SİMÜLASYON SERVİSİ               │
│                                                          │
│  1. system_config'den simulated_date oku                 │
│  2. simulated_date += 1 ay                               │
│  3. reviews_clean.json'dan o ayın review'larını al       │
│  4. Daha önce işlenmemiş olanları filtrele               │
│     (reviews tablosunda reviewId kontrolü)               │
│  5. Pipeline'ı tetikle                                   │
│     → processor.py (Claude)                              │
│     → embedder.py (OpenAI)                               │
│     → vector_store.py (Qdrant)                           │
│     → aggregator.py (PostgreSQL)                         │
│  6. simulated_date'i güncelle                            │
│  7. Aylık raporu üret + email gönder                     │
│     (PM notları rapor metnine dahil değil,               │
│      pm_sections olarak ayrı servis edilir)              │
└──────────────────┬───────────────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  Frontend güncellenir │
        │  • Grafikler yenilenir│
        │  • "✓ Tamamlandı"    │
        │    bildirimi gelir    │
        └──────────────────────┘
```


---

## KULLANICI DASHBOARD AKIŞI

```
PM dashboard'a giriyor
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│  ÜST BAR: Simüle Tarih: Ekim 2025  [ → Sonraki Ay ]        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│    SOL PANEL                        SAĞ PANEL              │
│    (Grafikler)                      (AI Chat)              │
│                                                            │
│  ┌─────────────────────┐        ┌───────────────────────┐  │
│  │ • Aylık puan        │        │ Kullanıcı:            │  │
│  │   trendi (çizgi)    │        │ "Mart'tan sonra veri  │  │
│  │                     │        │  kalitesi şikayeti    │  │
│  │ • Konu dağılımı     │        │  azaldı mı?"          │  │
│  │   (pasta grafik)    │        │                       │  │
│  │                     │        │ AI (tool calling):    │  │
│  │ • Sentiment trendi  │        │  → get_trend()        │  │
│  │   (çizgi grafik)    │        │    PostgreSQL'e gider │  │
│  │                     │        │  → search_examples()  │  │
│  │ • Şirket büyüklüğü  │        │    Qdrant'a gider     │  │
│  │   karşılaştırması   │        │                       │  │
│  │   (bar grafik)      │        │ "Evet, %23 azaldı.    │  │
│  │                     │        │  İşte detaylar..."    │  │
│  │ Filtreler:          │        │                       │  │
│  │ • Tarih aralığı     │        │ ─────────────────     │  │
│  │ • Şirket büyüklüğü  │        │                       │  │
│  │ • Konu              │        │ [ Rapora Ekle ]       │  │
│  │ • Puan              │        │  (tek buton, her zaman│  │
│  └─────────────────────┘        │   en son rapor ayına) │  │
│                                 └───────────────────────┘  │
└────────────────────────────────────────────────────────────┘
         │
         │  PM ilginç bir şey görüyor
         │  AI'a soruyor → cevabı beğeniyor
         │  "Rapora Ekle" tıklar
         ▼
┌──────────────────────────────────────────────────────┐
│  POST /reports/{simulated_date - 1 ay}/append        │
│                                                      │
│  Task ANINDA "tamamlandı" olarak kaydedilir          │
│  (prompt = PM sorusu, result = AI cevabı,            │
│   chart_data = varsa grafik verisi)                  │
│                                                      │
│  → ReportResponse içinde pm_sections olarak döner   │
│    (rapor metni content alanından ayrıdır)           │
└──────────────────────────────────────────────────────┘
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
│  • Analitik / trend  → get_trend()                          │
│  • Dağılım kırılımı  → get_breakdown()                      │
│  • Semantik / örnek  → search_examples()                    │
│  • Rapor listesi     → list_reports()                       │
│  • Rapor metni       → get_report()                         │
│  • PM notları        → get_report_notes()                   │
│  • Kombine sorgular  → birden fazla tool                    │
└──────────────┬──────────────────────────────────────────────┘
               │
    ┌──────────┼──────────────────┬────────────────────────────┐
    │          │                  │                            │
    ▼          ▼                  ▼                            ▼
┌────────────┐ ┌──────────────┐ ┌───────────────────┐ ┌────────────────┐
│ get_trend()│ │get_breakdown │ │ search_examples() │ │ list_reports() │
│            │ │()            │ │                   │ │ get_report()   │
│ • topic    │ │ • group_by:  │ │ • query (doğal    │ │ get_report_    │
│ • date_    │ │   topic /    │ │   dil)            │ │ notes()        │
│   from/to  │ │   sentiment /│ │ • topic,          │ │                │
│ • sentiment│ │   company_   │ │   sentiment,      │ │ → reports ve   │
│ • company_ │ │   size       │ │   company_size,   │ │   task_queue   │
│   size     │ │ • tarih/     │ │   top_k           │ │   tablolarından│
│ • rating_  │ │   rating/    │ │                   │ │                │
│   min/max  │ │   sentiment  │ │ → Qdrant'a gider  │ └───────┬────────┘
│ • visualize│ │   filtreleri │ │   Semantik        │         │
│            │ │ • visualize  │ │   benzerlik       │         │
│ → reviews  │ │              │ │   + metadata      │         │
│   tablosu  │ │ → reviews    │ │   filtresi        │         │
└─────┬──────┘ │   tablosu    │ └─────────┬─────────┘         │
      │        └──────┬───────┘           │                   │
      └───────────────┴───────────────────┴───────────────────┘
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

## AI CHAT — YANIT YAPISI (ChatResult)

```
POST /chat → { answer, chart_data }

answer     : string       ← Türkçe açıklama metni

chart_data : [            ← Sadece visualize=true olan tool çağrıları (0-2 arası)
  {
    type  : "trend",
    title : "Veri Kalitesi — Negatif Trend",
    data  : [
      { month: "2025-08", avg_rating: 4.2, count: 12 },
      ...
    ]
  },
  {
    type    : "breakdown",
    group_by: "topic" | "sentiment" | "company_size",
    title   : "Konu Dağılımı",
    data    : [
      { group_value: "veri kalitesi", count: 28, avg_rating: 2.1 },
      ...
    ]
  },
  {
    type  : "examples",
    title : "İlgili Review Örnekleri",
    data  : [
      { date, rating, company_size, topics[], sentiment, summary },
      ...
    ]
  }
]
```

Frontend chart tipine göre bileşen seçer:
• "trend"     → LineChart  (x = month, y = avg_rating veya count)
• "breakdown" → BarChart   (x = group_value, y = count veya avg_rating)
• "examples"  → ReviewCard listesi (alıntı metni gösterimi)

Not: `list_reports`, `get_report`, `get_report_notes` tool'ları grafik üretmez.


---

## POSTGRESQL ŞEMA

```
reviews
────────────────────────────────────
id            UUID  PK
review_id     TEXT  UNIQUE          ← duplicate koruması
likes         TEXT
dislikes      TEXT
rating        FLOAT
date          DATE
company_size  TEXT
topics        TEXT[]
sentiment     TEXT
summary       TEXT
created_at    TIMESTAMP

review_aggregates
────────────────────────────────────
month         DATE   (Ay bazlı)
topic         TEXT
sentiment     TEXT
company_size  TEXT
count         INT
PK: (month, topic, sentiment, company_size)

task_queue
────────────────────────────────────
id            UUID  PK
prompt        TEXT
target_date   DATE
status        TEXT   (bekliyor / tamamlandı)
result        TEXT
created_at    TIMESTAMP

reports
────────────────────────────────────
id            UUID  PK
month         DATE  UNIQUE  ← ayın 1'i (2025-08-01 gibi)
content       TEXT          ← markdown rapor metni
created_at    TIMESTAMP

system_config
────────────────────────────────────
key           TEXT  PK
value         TEXT

-- Anahtarlar:
-- simulated_date    başlangıç: '2025-07-01'
-- pipeline_running  'true' / 'false'  (zaten çalışıyor kontrolü için kritik)
-- pipeline_last_run NULL  ← kod tarafından set edilmiyor, hep null döner
```


---

## TECH STACK

| Katman        | Teknoloji                              |
|---------------|----------------------------------------|
| Veri Kaynağı  | Local JSON (770 review, önceden çekildi)|
| Embedding     | OpenAI text-embedding-3-small          |
| Vector Store  | Qdrant (semantik arama)                |
| AI            | Claude API — haiku-4-5-20251001        |
| Backend       | FastAPI                                |
| Frontend      | React + Recharts                       |
| Veritabanı    | PostgreSQL (aggregates + task queue + config)|
| Email         | SendGrid                               |
| Simülasyon    | POST /simulation/advance (manual tetik)|
| Deploy        | Hugging Face Spaces                    |


---

## ZAMAN TAHMİNİ

| Görev                                         | Süre        |
|-----------------------------------------------|-------------|
| PostgreSQL şema + Alembic migration           | 1 saat      |
| JSON loader + simülasyon servisi              | 1 saat      |
| Claude API veri işleme (processor.py)         | 2 saat      |
| OpenAI embedding + Qdrant entegrasyonu        | 1 saat      |
| Aggregator (PostgreSQL yazma)                 | 1 saat      |
| FastAPI backend + simulation route            | 2 saat      |
| Claude API tool calling (get_trend + get_breakdown + search)  | 2 saat      |
| Task queue + reporter.py                      | 1 saat      |
| SendGrid email                                | 1 saat      |
| React frontend + grafikler                    | 4 saat      |
| Test + debug                                  | 3 saat      |
| Deploy (Hugging Face Spaces)                  | 2 saat      |
| **TOPLAM**                                    | **21 saat** |


---

## TAKVİM

| Gün        | Yapılacak                                                    |
|------------|--------------------------------------------------------------|
| 29 Haziran | PostgreSQL şema + loader + processor + embedder + Qdrant     |
| 30 Haziran | FastAPI backend + simulation route + tool calling + frontend |
| 1 Temmuz   | Chat UI + task queue + reporter + email + deploy             |
| 2-3 Temmuz | Buffer + rapor yazımı + teslim                               |
