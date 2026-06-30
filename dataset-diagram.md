# Apollo.io Product Review Intelligence System
## Veri Seti & Şema Diyagramı

---

## VERİ KAYNAĞI — `reviews_clean.json`

G2'den çekilmiş, temizlenmiş 770 Apollo.io review'ı.
Tarih aralığı: **Temmuz 2025 → Haziran 2026**

### Alanlar

| Alan | Tip | Null? | Örnek | Not |
|------|-----|-------|-------|-----|
| `reviewId` | string | ✗ | `"13041581"` | G2 benzersiz ID |
| `title` | string | ✗ | `"Really Good for Mapping..."` | Review başlığı |
| `date` | string (YYYY-MM-DD) | ✗ | `"2026-06-28"` | Yayın tarihi |
| `starRating` | float | ✗ | `5.0` | 0.0–5.0 arası (0.0 = parse hatası) |
| `likes` | string | %0.3 | `"Great for lead gen..."` | Olumlu kısım (`\|` öncesi) |
| `dislikes` | string | %0.3 | `"Email verification slow..."` | Olumsuz kısım (`\|` sonrası) |
| `company_size` | string | %30.1 | `"Small-Business (50 or fewer emp.)"` | reviewerInfo'dan parse edildi |
| `reviewerName` | string | ✗ | `"Kunal P."` | Reviewer adı |
| `reviewerTitle` | string | %4.9 | `"Analyst"` | İş unvanı |
| `reviewerInfo` | array | %30.1 | `["Small-Business...", "IT and Services"]` | Ham G2 verisi |
| `productName` | string | ✗ | `"Apollo.io"` | — |
| `productSlug` | string | ✗ | `"apollo-io"` | — |
| `incentivized` | bool | ✗ | `true` | G2 teşvikli review mi? |
| `reviewSource` | string | ✗ | `"Organic"` | — |
| `validatedReviewer` | bool | ✗ | `true` | G2 doğrulaması |
| `verifiedCurrentUser` | bool | ✗ | `true` | Aktif kullanıcı mı? |

### Dağılım İstatistikleri

**starRating:**
| Değer | Adet | Not |
|-------|------|-----|
| 0.0 | 13 | Scraper parse hatası, içerik geçerli |
| 0.5 | 4 | Scraper parse hatası |
| 1.0–2.5 | 21 | Düşük puanlı |
| 3.0–3.5 | 64 | Orta puanlı |
| 4.0–4.5 | 369 | Yüksek puanlı |
| 5.0 | 305 | En yüksek puan |

**company_size:**
| Değer | Adet |
|-------|------|
| Small-Business (50 or fewer emp.) | 301 |
| Mid-Market (51-1000 emp.) | 218 |
| Enterprise (> 1000 emp.) | 19 |
| Bilinmiyor (null) | 232 |

**Metin uzunluğu:**
| Alan | Ort. | Min | Max |
|------|------|-----|-----|
| `likes` | 244 karakter | 0 | 1240 |
| `dislikes` | 168 karakter | 0 | 946 |

**Aylık dağılım:**
| Ay | Adet |
|----|------|
| 2025-07 | 32 |
| 2025-08 | 104 |
| 2025-09 | 94 |
| 2025-10 | 68 |
| 2025-11 | 41 |
| 2025-12 | 79 |
| 2026-01 | 64 |
| 2026-02 | 36 |
| 2026-03 | 104 |
| 2026-04 | 73 |
| 2026-05 | 52 |
| 2026-06 | 23 |


---

## POSTGRESQL TABLOLARI

### `reviews`

Pipeline'dan geçmiş, LLM tarafından zenginleştirilmiş review'lar.

| Kolon | Tip | Kısıt | Açıklama |
|-------|-----|-------|----------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | İç ID |
| `review_id` | TEXT | UNIQUE NOT NULL | G2'den gelen `reviewId` — duplicate koruması |
| `likes` | TEXT | — | Olumlu kısım |
| `dislikes` | TEXT | — | Olumsuz kısım |
| `rating` | FLOAT | — | 0.0–5.0 |
| `date` | DATE | — | G2'deki yayın tarihi |
| `company_size` | TEXT | — | Small-Business / Mid-Market / Enterprise |
| `topics` | TEXT[] | — | Claude'un atadığı konu etiketleri |
| `sentiment` | TEXT | — | `pozitif` / `negatif` / `nötr` |
| `summary` | TEXT | — | Claude'un 1 cümlelik özeti |
| `created_at` | TIMESTAMP | DEFAULT now() | Pipeline'a girdiği zaman |

---

### `review_aggregates`

Dashboard grafikleri ve `get_trend()` / `get_breakdown()` tool'ları için önceden hesaplanmış aggregation.

Her review işlendiğinde `aggregator.py` bu tabloyu günceller.

| Kolon | Tip | Kısıt | Açıklama |
|-------|-----|-------|----------|
| `month` | DATE | PK (bileşik) | Ay bazlı (date_trunc('month', date)) |
| `topic` | TEXT | PK (bileşik) | Konu etiketi |
| `sentiment` | TEXT | PK (bileşik) | pozitif / negatif / nötr |
| `company_size` | TEXT | PK (bileşik) | Şirket büyüklüğü |
| `count` | INT | NOT NULL | O kombinasyonda kaç review var |

**Bileşik PK:** `(month, topic, sentiment, company_size)`

---

### `task_queue`

PM'in "Rapora Ekle" butonuyla kaydettiği soru-cevap çiftleri (pm_sections).

| Kolon | Tip | Kısıt | Açıklama |
|-------|-----|-------|----------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | — |
| `prompt` | TEXT | NOT NULL | PM'in AI'a sorduğu soru |
| `target_date` | DATE | NOT NULL | Hangi aya ait rapora eklendi (o anki `simulated_date - 1 ay`) |
| `status` | TEXT | DEFAULT 'tamamlandı' | Her zaman anında `tamamlandı` olarak kaydedilir |
| `result` | TEXT | — | AI'ın verdiği cevap (chat yanıtının `answer` alanı) |
| `chart_data` | JSONB | — | Varsa grafik verisi (chat yanıtının `chart_data` alanı) |
| `created_at` | TIMESTAMP | DEFAULT now() | — |

Not: task_queue artık "gelecek aya erteleme" mekanizması olarak kullanılmaz. Her "Rapora Ekle" aksiyonu anında `POST /reports/{month}/append` ile kaydedilir.

---

### `reports`

Claude'un her ay ürettiği markdown raporlar.

| Kolon | Tip | Kısıt | Açıklama |
|-------|-----|-------|----------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | — |
| `month` | DATE | UNIQUE NOT NULL | Ayın 1'i (2025-08-01 gibi) |
| `content` | TEXT | NOT NULL | Claude'un ürettiği markdown rapor metni |
| `created_at` | TIMESTAMP | DEFAULT now() | — |

`reporter.py` her pipeline sonunda bu tabloya upsert yapar (aynı aya ait rapor varsa üzerine yazar).

---

### `system_config`

PoC simülasyon durumu. Key-value store.

| Kolon | Tip | Kısıt | Açıklama |
|-------|-----|-------|----------|
| `key` | TEXT | PK | Config anahtarı |
| `value` | TEXT | — | Config değeri |

**Başlangıç kayıtları:**

| key | value | Açıklama |
|-----|-------|----------|
| `simulated_date` | `2025-07-01` | Mevcut simüle ay başı |
| `pipeline_running` | `false` | Pipeline kilidi — zaten çalışıyor mu? |
| `pipeline_last_run` | `null` | Son pipeline tarihi (kod set etmiyor, hep null) |


---

## QDRANT COLLECTION — `apollo_reviews`

Semantik arama için `search_examples()` tool'u tarafından kullanılır.

### Collection Yapısı

| Alan | Tip | Açıklama |
|------|-----|----------|
| `id` | UUID | Qdrant point ID (`reviews.id` ile aynı) |
| `vector` | float[1536] | OpenAI text-embedding-3-small çıktısı |
| `payload` | JSON | Filtrelenebilir metadata |

### Payload Şeması

```json
{
  "text": "Great for lead gen... | Email verification is slow...",
  "review_id": "13041581",
  "date": "2026-06-28",
  "rating": 5.0,
  "company_size": "Small-Business (50 or fewer emp.)",
  "topics": ["veri kalitesi", "UX"],
  "sentiment": "pozitif",
  "summary": "Kullanıcı lead generation konusunda memnun..."
}
```

### Embedding Kaynağı

`likes + " | " + dislikes` → tek metin → OpenAI API → vector[1536]


---

## TABLO İLİŞKİLERİ

```
reviews_clean.json (kaynak)
         │
         │  loader.py: date filtresi ile aylık slice
         ▼
    reviews tablosu
    review_id (UNIQUE) ──── duplicate koruması
         │
         │  Her INSERT'ten sonra aggregator.py tetiklenir
         ▼
review_aggregates tablosu
    (month, topic, sentiment, company_size, count)
         │
         │  get_trend() tool'u bu tabloyu sorgular
         ▼
    AI Chat cevabı

    reviews tablosu
         │
         │  embedder.py → vector_store.py
         ▼
    Qdrant collection
    point.id = reviews.id   ──── ID eşleşmesi
         │
         │  search_examples() tool'u bu collection'ı sorgular
         ▼
    AI Chat cevabı

task_queue tablosu
    target_date ──────────── simulated_date - 1 ay (en son üretilen rapor)
    status: her zaman anında "tamamlandı"
    POST /reports/{month}/append ile kaydedilir
    GET /reports/{month} → pm_sections olarak döner
```


---

## VERİ DÖNÜŞÜM AKIŞI

```
reviews_clean.json
    review_id   ──────────────────────────────────► reviews.review_id
    likes       ──────────────────────────────────► reviews.likes
    dislikes    ──────────────────────────────────► reviews.dislikes
    starRating  ──────────────────────────────────► reviews.rating
    date        ──────────────────────────────────► reviews.date
    company_size ─────────────────────────────────► reviews.company_size
                    ┌── Claude API (processor.py) ─► reviews.topics[]
                    │                              ► reviews.sentiment
                    │                              ► reviews.summary
                    │
                    └── OpenAI API (embedder.py)  ─► Qdrant vector[1536]

reviews (zenginleşmiş)
    (month, topic, sentiment, company_size) ──────► review_aggregates.count++
```


---

## KONU ETİKETLERİ (Claude tarafından atanacak)

Processor.py'nin Claude'a önereceği standart etiket listesi:

| Etiket | Açıklama |
|--------|----------|
| `veri kalitesi` | Yanlış/eksik contact bilgisi, bounce rate |
| `fiyat` | Pahalı, fiyat artışı, plan değişikliği |
| `email deliverability` | Email ulaşmaması, spam sorunu |
| `UX / kullanım kolaylığı` | Arayüz, öğrenme eğrisi, hız |
| `müşteri desteği` | Destek kalitesi, yanıt süresi |
| `entegrasyon` | CRM entegrasyonu, API, Zapier |
| `arama & filtreleme` | Prospecting, filtre kalitesi |
| `otomasyon` | Sequence, workflow özellikleri |
| `raporlama & analitik` | Dashboard, insight eksikliği |
| `genel olumlu` | Genel memnuniyet, öneri |
