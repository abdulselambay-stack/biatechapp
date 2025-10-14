# WhatsApp Cloud API - Mesaj Gönderim ve İzleme Sistemi

Bu sistem WhatsApp Cloud API kullanarak toplu mesaj gönderimi ve webhook izleme işlevlerini sağlar. **Önemli özellik:** Aynı şablon mesajı daha önce gönderilmiş kişilere tekrar gönderilmez.

## 🌟 Özellikler

- ✅ **Toplu Mesaj Gönderimi**: Belirttiğiniz sayıda kişiye (örn: 225) şablon mesajı gönderin
- ✅ **Duplicate Kontrolü**: Aynı şablon mesajı aynı kişiye tekrar gönderilmez
- ✅ **Webhook İzleme**: Mesaj durumlarını (delivered, read, sent, failed) gerçek zamanlı takip edin
- ✅ **Mesaj Geçmişi**: Hangi şablonun kime gönderildiğini JSON dosyasında saklayın
- ✅ **Web Arayüzü**: Kullanıcı dostu web paneli ile tüm işlemleri yönetin
- ✅ **İstatistikler**: Toplam kişi, şablon ve gönderilen mesaj sayılarını görüntüleyin

## 📋 Gereksinimler

- Python 3.8+
- WhatsApp Business API erişimi
- Meta Developer hesabı
- Onaylanmış mesaj şablonları

## 🚀 Kurulum

### 1. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### 2. Ortam Değişkenlerini Ayarlayın

`.env.example` dosyasını `.env` olarak kopyalayın ve bilgilerinizi girin:

```bash
cp .env.example .env
```

`.env` dosyasını düzenleyin:

```env
WHATSAPP_ACCESS_TOKEN=your_actual_access_token
PHONE_NUMBER_ID=your_phone_number_id
VERIFY_TOKEN=technoglobal123
```

**WhatsApp API bilgilerinizi bulmak için:**
1. https://developers.facebook.com/ adresine gidin
2. WhatsApp uygulamanızı seçin
3. "WhatsApp" > "API Setup" bölümünden:
   - **Phone Number ID**: Test numarası altında bulunur
   - **Access Token**: "Temporary access token" veya kalıcı token oluşturun

### 3. Kişi Listesini Hazırlayın

`contacts_with_index.json` dosyanız şu formatta olmalı:

```json
[
  {
    "id": "905551234567",
    "name": "Ali Yılmaz",
    "index": 1
  },
  {
    "id": "905559876543",
    "name": "Ayşe Demir",
    "index": 2
  }
]
```

**Not:** Numaralar ülke kodu ile başlamalı (Türkiye için 90)

### 4. Uygulamayı Başlatın

```bash
python app.py
```

Uygulama http://localhost:5005 adresinde çalışacaktır.

## 🌐 Webhook Kurulumu

### Ngrok ile Geliştirme Ortamında Test

```bash
# Ngrok kurun (ilk kez)
brew install ngrok  # macOS
# veya https://ngrok.com/download

# Tunnel oluşturun
ngrok http 5005
```

Ngrok size bir public URL verecektir (örn: `https://abc123.ngrok.io`)

### Meta Developer Console'da Webhook Ayarlama

1. https://developers.facebook.com/ adresine gidin
2. WhatsApp uygulamanızı seçin
3. "WhatsApp" > "Configuration" > "Webhook"
4. **Callback URL**: `https://your-domain.com/webhook` (ngrok URL'i)
5. **Verify Token**: `technoglobal123` (veya .env'deki değer)
6. **Webhook Fields**: `messages` ve `message_status` seçin
7. "Verify and Save" tıklayın

## 📱 Kullanım

### Web Arayüzü

http://localhost:5005 adresine tarayıcıdan bağlanın.

#### Mesaj Gönderme:
1. **Şablon Adı**: Meta Business'ta onaylanmış şablon adını girin (örn: `hello_world`)
2. **Kişi Sayısı**: Kaç kişiye göndermek istediğinizi belirtin (örn: 225)
3. **Dil Kodu**: Şablonun dil kodunu seçin (tr, en, ar)
4. "Gönder" butonuna tıklayın

**Önemli:** Sistem otomatik olarak daha önce bu şablonu almamış kişileri seçer!

### API Kullanımı

#### 1. Mesaj Gönder

```bash
curl -X POST http://localhost:5005/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "hello_world",
    "limit": 225,
    "language_code": "tr"
  }'
```

**Response:**
```json
{
  "success": true,
  "template": "hello_world",
  "total_selected": 225,
  "total_eligible": 1500,
  "successful_sends": 220,
  "failed_sends": 5,
  "results": [...]
}
```

#### 2. Mesaj Geçmişini Görüntüle

```bash
curl http://localhost:5005/api/history
```

#### 3. Webhook Loglarını Görüntüle

```bash
curl http://localhost:5005/api/webhook-logs?limit=50
```

#### 4. Duplicate Kontrolü

```bash
curl -X POST http://localhost:5005/api/check-duplicates \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "hello_world",
    "phone_numbers": ["905551234567", "905559876543"]
  }'
```

## 📊 Dosya Yapısı

```
wpCloud/
├── app.py                        # Ana uygulama
├── webhook.py                    # Eski webhook (artık kullanılmıyor)
├── requirements.txt              # Python bağımlılıkları
├── .env                          # Ortam değişkenleri (GİZLİ)
├── .env.example                  # Örnek ortam değişkenleri
├── README.md                     # Bu dosya
├── contacts_with_index.json     # Kişi listesi
├── message_history.json         # Gönderim geçmişi (otomatik oluşur)
└── webhook_logs.json            # Webhook logları (otomatik oluşur)
```

## 🔒 Duplicate Önleme Sistemi

Sistem `message_history.json` dosyasında şu yapıyı kullanır:

```json
{
  "hello_world": [
    "905551234567",
    "905559876543"
  ],
  "order_confirmation": [
    "905551234567"
  ]
}
```

**Mantık:**
1. Mesaj gönderilmeden önce `message_history.json` kontrol edilir
2. Bu şablonu daha önce almamış kişiler filtrelenir
3. Limit kadar kişi seçilir
4. Başarıyla gönderilen numaralar geçmişe eklenir

**Örnek Senaryo:**
- **Gün 1**: `hello_world` şablonunu 225 kişiye gönderdiniz
- **Gün 2**: Aynı şablonu tekrar 225 kişiye göndermek istiyorsunuz
- **Sonuç**: Sistem dün gönderilen 225 kişiyi atlar, geri kalan listeden 225 yeni kişi seçer!

## 🔍 Webhook Takibi

Webhook logları `webhook_logs.json` dosyasında saklanır ve şunları içerir:

- **Mesaj Durumları**: sent, delivered, read, failed
- **Gelen Mesajlar**: Kullanıcılardan gelen cevaplar
- **Timestamp**: Her olay için zaman damgası
- **Mesaj ID**: WhatsApp mesaj ID'si

Web arayüzünde gerçek zamanlı olarak (10 saniyede bir yenilenir) takip edilir.

## ⚠️ Önemli Notlar

### 1. Rate Limiting
WhatsApp Cloud API Tier 1 limitleri:
- **Tier 1**: 1,000 unique recipients / 24 hours
- **Mesajlama Hızı**: ~80 mesaj/saniye (max)

Günlük 225 kişi göndermek Tier 1 için uygundur.

### 2. Şablon Onayı
Göndereceğiniz tüm mesajların Meta Business'ta onaylanmış olması gerekir:
1. Meta Business Manager > WhatsApp Manager
2. "Message Templates"
3. Şablon oluşturun ve onay bekleyin (24-48 saat)

### 3. Test Numara Limiti
Geliştirme modunda 5 test numarasına kadar gönderebilirsiniz. Production'a geçmek için Business Verification gerekir.

## 🛠️ Sorun Giderme

### "Verification failed" hatası
- `.env` dosyasındaki `VERIFY_TOKEN` değerini kontrol edin
- Meta Developer Console'daki Verify Token ile eşleşmeli

### "Template not found" hatası
- Şablon adını doğru yazdığınızdan emin olun
- Şablonun onaylanmış olduğunu kontrol edin
- Dil kodunun doğru olduğunu kontrol edin

### "Invalid access token" hatası
- Access token'ın geçerli olduğundan emin olun
- Token süresiz olmalı (kalıcı token oluşturun)

### Webhook çalışmıyor
- Ngrok tunnel'ının aktif olduğundan emin olun
- Meta Console'da webhook URL'in doğru olduğunu kontrol edin
- `messages` ve `message_status` field'larının seçili olduğunu kontrol edin

## 📈 Örnek Kullanım Senaryosu

**Durum:** 10,000 kişilik listeniz var, her gün 225 kişiye "daily_offer" şablonunu göndermek istiyorsunuz.

**Gün 1:**
```bash
# İlk 225 kişiye gönder
curl -X POST http://localhost:5005/api/send \
  -H "Content-Type: application/json" \
  -d '{"template_name": "daily_offer", "limit": 225}'
```
→ İlk 225 kişiye gönderilir, geçmişe kaydedilir.

**Gün 2:**
```bash
# Aynı komutu tekrar çalıştırın
curl -X POST http://localhost:5005/api/send \
  -H "Content-Type: application/json" \
  -d '{"template_name": "daily_offer", "limit": 225}'
```
→ 226-450 arası kişilere gönderilir (ilk 225 atlanır).

**Gün 3-44:** Aynı şekilde devam eder, 44 günde tüm listeyi kaplar!

## 📞 Destek

Sorularınız için:
- WhatsApp Business API Dokümantasyonu: https://developers.facebook.com/docs/whatsapp
- Meta Developer Community: https://developers.facebook.com/community/

## 📝 Lisans

Bu proje kişisel kullanım içindir.
