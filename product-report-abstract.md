# Apollo.io Aylık Ürün İstihbarat Raporu — Şablon

Her ayın simülasyon pipeline'ı tamamlandığında Claude tarafından otomatik üretilir
ve SendGrid üzerinden ilgili kişilere iletilir.

---

## 1. Metrikler

**Bu ay**
- Toplam review sayısı
- Ortalama puan (★ / 5.0)
- Puan dağılımı: 5★ · 4★ · 3★ · 2★ · 1★ kaçar adet

**Geçen aya göre değişim**
- Ortalama puan farkı (örn. "geçen aya göre +0.2")
- Review hacmi değişimi

> Kaynak: `reviews` tablosu — `rating`, `date` alanları

---

## 2. Konu Analizi

**En çok şikayet edilen 5 konu** (negatif sentiment, bu ay)

| Konu | Adet | Geçen aya göre |
|------|------|----------------|
| …    | …    | ↑ %X / ↓ %X   |

**En çok övülen 5 konu** (pozitif sentiment, bu ay)

| Konu | Adet | Geçen aya göre |
|------|------|----------------|
| …    | …    | …              |

**Öne çıkan değişim** — Bir önceki aya kıyasla belirgin hareket eden konular
(örn. "fiyat şikayeti geçen aya göre %40 arttı")

> Kaynak: `review_aggregates` — `(month, topic, sentiment, count)` kombinasyonları

---

## 3. Segment Analizi

**Şirket büyüklüğüne göre** — Small-Business · Mid-Market · Enterprise · bilinmiyor

Her segment için:
- En sık şikayet konusu
- Ortalama puan
- Review hacmi

> Kaynak: `review_aggregates.company_size` + `reviews.rating`

---

## 4. Trend (Son 6 Ay)

- Aylık ortalama puan grafiği
- En büyük 3 konunun aylık seyri (örn. "veri kalitesi" şikayeti Ağustos'tan beri düşüyor mu?)

> Kaynak: `review_aggregates` — `month` bazında gruplama
> Not: Anlamlı trend verisi için en az 3 aylık birikmiş veri gerekir.

---

## 5. Aksiyon Önerileri

Claude, yukarıdaki verileri sentezleyerek üretir:

- **Bu ayın en kritik 3 problemi** ve önerilen aksiyon
- **İzlenmesi gereken sinyal** — henüz küçük ama yükselen bir konu varsa öne çıkar

> Kaynak: Tüm tablolar — Claude API (reporter.py)

---

## 6. PM Özel Analizleri

Bir önceki simülasyon döneminde PM'in "Rapora Ekle" ile kuyruğa attığı sorgular
bu bölümde yanıtlanmış olarak yer alır.

**Nasıl çalışır:**
1. PM, AI chat panelinde bir soruyu araştırır
   - `get_trend(topic, date_from, date_to, ...)` → PostgreSQL'den aylık avg_rating + count trendi
   - `get_breakdown(group_by, ...)` → Konu / sentiment / şirket büyüklüğü kırılımı
   - `search_examples(query, filters, top_k)` → Qdrant'tan semantik örnek review'lar
2. Cevabı beğenirse "Rapora Ekle → Gelecek Ay" butonuna basar
3. Sorgu `task_queue` tablosuna `status: bekliyor` olarak düşer
4. Sonraki pipeline çalışınca reporter.py bu task'ları da işler ve rapora ekler

**PM'in sorabileceği sorgu örnekleri:**
- "Enterprise müşteriler veri kalitesinden mi yoksa fiyattan mı daha çok şikayet ediyor?"
- "Email deliverability şikayetleri son 3 ayda artıyor mu, azalıyor mu?"
- "Otomasyon özelliğini seven kullanıcılar başka hangi konulardan memnun?"
- "4 yıldız veren ama yine de dislikes yazan kullanıcıların ortak şikayeti ne?"

> Kaynak: `task_queue` tablosu — `prompt`, `target_date`, `result` alanları

---

## Kapsam Dışı

Veri kısıtları nedeniyle bu raporda **yer almayan** bölümler:

| Bölüm | Neden |
|-------|-------|
| Sektöre göre segment | `industry` alanı veri setinde %86 null |
| Rakip karşılaştırması | Etiket listesinde rakip mention yok |
| NPS (gerçek veya yaklaşık) | `reporter.py` hesaplamıyor; promoter/detractor mantığı kodda yok |
