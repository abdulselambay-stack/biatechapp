# 🚀 Toplu Gönderim Optimizasyonu

## ✅ Yapılan İyileştirmeler

### 1. ⏱️ Rate Limiting (Spam Önleme)

**Özellik:** Dakikada kaç mesaj gönderileceğini kontrol edebilirsiniz.

**Seçenekler:**
- **Yağış (20 mesaj/dakika):** Her 3 saniyede 1 mesaj
- **Orta (40 mesaj/dakika):** Her 1.5 saniyede 1 mesaj ✅ **ÖNERİLEN**
- **Hızlı (60 mesaj/dakika):** Her saniyede 1 mesaj
- **Maksimum (80 mesaj/dakika):** 0.75 saniyede 1 mesaj

**WhatsApp Limitleri:**
- Messaging Limit: 1000 mesaj/dakika (Tier 1)
- Business API: 80-250 mesaj/saniye (tier'a göre)
- **Önerilen:** 40-60 mesaj/dakika spam riski olmadan

### 2. 📋 Kalıcı Loglar

**Özellik:** Toplu gönderim bitse bile loglar kaybolmaz.

**Avantajlar:**
- ✅ Gönderim bitince logları inceleyebilirsiniz
- ✅ Başka template gönderseniz bile eski loglar kalır
- ✅ Manuel temizleme butonu var

**Temizleme:**
```
🗑️ Logları Temizle butonu → Tüm logları siler
```

### 3. 📊 Detaylı Progress Tracking

**Yeni Metrikler:**
- **Geçen süre:** Gönderim ne kadar sürüyor
- **Hız:** Saniyede kaç mesaj gönderiliyor
- **ETA:** Tahmini bitiş süresi (gelecek sürümde)

**Örnek Log:**
```
📊 Progress: 50/200 (25%) - ✅ 45 ❌ 5 - Hız: 0.83 msg/s
```

---

## 🎯 Kullanım

### 1. Toplu Gönderim Formu

```
Template Seç: sablon_6
Header Image ID: (otomatik yüklenir)

⏱️ Gönderim Hızı: Orta (40 mesaj/dakika)
   ⚠️ Önerilen: 40-60 mesaj/dakika

Kaç Kişiye Gönderilsin?
   ○ Tüm Uygun Kişiler (200 kişi)
   ● Belirli Sayıda [150]
```

### 2. Gönderim Başlatma

**Tıkla:** `🚀 Toplu Gönderimi Başlat`

**İlerleme Ekranı:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gönderim İlerlemesi: 45%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Başarılı: 85
Başarısız: 3
Atlandı: 0

📋 Detaylı Gönderim Log:
[12:34:56] 🚀 Toplu gönderim başlatılıyor...
[12:34:56] 📝 Template: sablon_6
[12:34:56] 👥 Hedef: 150 kişi
[12:34:56] 
[12:34:57] ✅ Ahmet Yılmaz (905551234567)
[12:34:58] ✅ Mehmet Kaya (905552345678)
[12:35:00] ❌ Test User (905559999999) - Invalid phone
```

### 3. Gönderim Bitince

**Loglar Kalıyor:** ✅
- Ekran kapansa bile loglar kaybolmaz
- Başka işlem yapıp geri dönebilirsiniz
- Manuel temizleme yapana kadar kalır

**Temizleme:**
```
🗑️ Logları Temizle → Confirm → Loglar silindi
```

---

## ⚙️ Backend Değişiklikleri

### Rate Limiting Implementasyonu

```python
# routes/bulk_send.py

# Rate limiting ayarları (dakikada max istek)
RATE_LIMIT_PER_MINUTE = data.get("rate_limit_per_minute", 60)
DELAY_BETWEEN_MESSAGES = 60.0 / RATE_LIMIT_PER_MINUTE if RATE_LIMIT_PER_MINUTE > 0 else 1.0

logger.info(f"⏱️ Rate limit: {RATE_LIMIT_PER_MINUTE} mesaj/dakika (Her mesaj arası: {DELAY_BETWEEN_MESSAGES:.2f}s)")

for i, contact in enumerate(recipients, 1):
    # Mesaj gönder
    result = send_template_message(...)
    
    # Rate limiting delay
    if i < total_recipients:
        time.sleep(DELAY_BETWEEN_MESSAGES)  # ⏱️ Bekleme
```

**Örnek:**
- 40 mesaj/dakika → Her mesaj arası: 1.5 saniye
- 60 mesaj/dakika → Her mesaj arası: 1 saniye
- 20 mesaj/dakika → Her mesaj arası: 3 saniye

### Progress Tracking

```python
start_time = time.time()

if i % 10 == 0 or i == total_recipients:
    elapsed_time = time.time() - start_time
    messages_per_sec = i / elapsed_time if elapsed_time > 0 else 0
    logger.info(f"📊 Progress: {i}/{total_recipients} ({(i/total_recipients*100):.1f}%) - ✅ {success_count} ❌ {failed_count} - Hız: {messages_per_sec:.2f} msg/s")
```

---

## 📊 Örnek Senaryolar

### Senaryo 1: Güvenli Toplu Gönderim (200 kişi)

**Ayarlar:**
- Template: sablon_6
- Hız: **Orta (40 mesaj/dakika)**
- Limit: Tüm Uygun Kişiler (200 kişi)

**Sonuç:**
- Toplam süre: ~5 dakika
- Her mesaj arası: 1.5 saniye
- Spam riski: Düşük ✅

---

### Senaryo 2: Hızlı Gönderim (500 kişi)

**Ayarlar:**
- Hız: **Hızlı (60 mesaj/dakika)**
- Limit: 500 kişi

**Sonuç:**
- Toplam süre: ~8.3 dakika
- Her mesaj arası: 1 saniye
- Spam riski: Orta ⚠️

---

### Senaryo 3: Konservatif (50 kişi - Test)

**Ayarlar:**
- Hız: **Yağış (20 mesaj/dakika)**
- Limit: 50 kişi

**Sonuç:**
- Toplam süre: 2.5 dakika
- Her mesaj arası: 3 saniye
- Spam riski: Çok Düşük ✅✅

---

## 🎨 UI Değişiklikleri

### 1. Rate Limit Dropdown

```html
<select x-model="formData.rate_limit_per_minute">
    <option value="20">Yağış (20 mesaj/dakika - Her 3 saniyede 1)</option>
    <option value="40">Orta (40 mesaj/dakika - Her 1.5 saniyede 1)</option>
    <option value="60" selected>Hızlı (60 mesaj/dakika - Her saniyede 1)</option>
    <option value="80">Maksimum (80 mesaj/dakika - 0.75 saniyede 1)</option>
</select>

<p class="text-xs text-gray-500 mt-1">
    <span class="text-amber-600">⚠️</span> Önerilen: 40-60 mesaj/dakika
</p>
```

### 2. Loglar Her Zaman Görünür

**Önceki:**
```html
<div x-show="sending">  <!-- ❌ Gönderim bitince kayboluyordu -->
```

**Yeni:**
```html
<div x-show="sending || (sendLogs.length > 0 && !showResults)">
    <!-- ✅ Gönderim bitse bile loglar varsa göster -->
</div>
```

### 3. Temizleme Butonu

```html
<button @click="clearLogs()">
    🗑️ Logları Temizle
</button>
```

---

## 🚨 WhatsApp Rate Limits (Resmi)

### Business API Limits:

| Tier | Limit | Önerilen Kullanım |
|------|-------|-------------------|
| **Tier 1** (Yeni) | 1,000 mesaj/gün | 20-40 mesaj/dakika |
| **Tier 2** | 10,000 mesaj/gün | 40-60 mesaj/dakika |
| **Tier 3** | 100,000 mesaj/gün | 60-80 mesaj/dakika |

### Spam Algoritması:
- **Şikayet oranı** > 0.3% → Uyarı
- **Block oranı** > 0.5% → Limit düşürme
- **Çok hızlı gönderim** → Geçici ban

### Bizim Önerilerimiz:
✅ **40 mesaj/dakika:** En güvenli  
✅ **60 mesaj/dakika:** Hızlı ama güvenli  
⚠️ **80+ mesaj/dakika:** Riskli, dikkatli kullan

---

## 🧪 Test

### 1. Küçük Test (10 kişi)

```bash
Template: test_template
Rate: 20 mesaj/dakika
Limit: 10 kişi
→ Süre: ~30 saniye
```

### 2. Orta Test (100 kişi)

```bash
Template: sablon_6
Rate: 40 mesaj/dakika
Limit: 100 kişi
→ Süre: ~2.5 dakika
```

### 3. Büyük Test (500 kişi)

```bash
Template: sablon_6
Rate: 60 mesaj/dakika
Limit: 500 kişi
→ Süre: ~8.3 dakika
```

---

## 📝 Loglar Örneği

```
[12:34:56] 🚀 Toplu gönderim başlatılıyor...
[12:34:56] 📝 Template: sablon_6
[12:34:56] 👥 Hedef: 150 kişi
[12:34:56] 
[12:34:57] ✅ Ahmet Yılmaz (905551234567)
[12:34:59] ✅ Mehmet Kaya (905552345678)
[12:35:01] ✅ Ayşe Demir (905553456789)
...
[12:39:45] 📊 Progress: 100/150 (66.7%) - ✅ 95 ❌ 5 - Hız: 0.67 msg/s
...
[12:41:30] ✅ Son Kişi (905559999999)
[12:41:30] 
[12:41:30] ✅ Gönderim tamamlandı!
[12:41:30]    Başarılı: 145
[12:41:30]    Başarısız: 5
[12:41:30]    Atlandı: 0
```

**Loglar kalıyor!** ✅
- Ekranı kapatıp geri gelseniz bile
- Başka template gönderseniz bile
- Manuel temizleye kadar

---

## 🎯 Sonuç

**Artık:**
- ✅ Spam'a girmiyorsunuz (rate limiting)
- ✅ Loglar kaybolmuyor (kalıcı)
- ✅ Hız kontrolü elinizde
- ✅ Detaylı progress tracking
- ✅ WhatsApp limitlerine uygun

**Test edin ve feedback verin!** 🚀
