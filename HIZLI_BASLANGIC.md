# 🚀 Hızlı Başlangıç Rehberi

## 1️⃣ Kurulum (2 dakika)

### Adım 1: Bağımlılıkları yükleyin
```bash
cd /Users/melkor/Desktop/technosender/wpCloud
pip install -r requirements.txt
```

### Adım 2: WhatsApp API bilgilerinizi girin
```bash
# .env.example dosyasını .env olarak kopyalayın
cp .env.example .env

# .env dosyasını düzenleyin
nano .env
```

`.env` dosyasına şunları yazın:
```env
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxx  # Meta Developer'dan alın
PHONE_NUMBER_ID=12345678901234    # Meta Developer'dan alın
VERIFY_TOKEN=technoglobal123
```

**API bilgilerinizi bulmak için:**
1. https://developers.facebook.com/ → WhatsApp uygulamanız
2. **Access Token**: API Setup → Temporary access token (veya kalıcı token)
3. **Phone Number ID**: API Setup → Phone number ID (test numarası altında)

### Adım 3: Uygulamayı başlatın
```bash
python app.py
```

✅ Uygulama başladı! → http://localhost:5005

---

## 2️⃣ İlk Mesajınızı Gönderin (1 dakika)

### Web Arayüzü Kullanarak:
1. Tarayıcıda http://localhost:5005 adresini açın
2. **Şablon Adı** kısmına Meta'da onaylı şablon adınızı yazın (örn: `hello_world`)
3. **Kişi Sayısı** kısmına kaç kişiye göndermek istediğinizi yazın (örn: `225`)
4. **Dil Kodu** seçin (Türkçe: `tr`)
5. **Gönder** butonuna tıklayın

### API ile Gönderme:
```bash
curl -X POST http://localhost:5005/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "hello_world",
    "limit": 225,
    "language_code": "tr"
  }'
```

---

## 3️⃣ Webhook'u Aktif Edin (5 dakika)

### Geliştirme için Ngrok kullanın:

```bash
# Ngrok kurun
brew install ngrok  # macOS için

# Tunnel başlatın
ngrok http 5005
```

Ngrok size bir URL verecek: `https://abc123.ngrok.io`

### Meta'da webhook ayarlayın:

1. https://developers.facebook.com/ → WhatsApp uygulamanız
2. **Configuration** → **Webhook**
3. **Callback URL**: `https://abc123.ngrok.io/webhook`
4. **Verify Token**: `technoglobal123`
5. **Subscribe to**: `messages` ve `message_status`
6. **Verify and Save**

✅ Webhook aktif! Artık mesaj durumlarını görebilirsiniz.

---

## 4️⃣ Duplicate Kontrolü Nasıl Çalışır?

### Senaryo: 10,000 kişilik liste, günlük 225 mesaj

**Gün 1:**
```bash
# hello_world şablonunu 225 kişiye gönder
python -c "import requests; requests.post('http://localhost:5005/api/send', json={'template_name': 'hello_world', 'limit': 225})"
```
→ Kişi #1 - #225 arası mesaj alır ✅

**Gün 2:** Aynı komutu tekrar çalıştırın
```bash
python -c "import requests; requests.post('http://localhost:5005/api/send', json={'template_name': 'hello_world', 'limit': 225})"
```
→ Kişi #226 - #450 arası mesaj alır ✅ (İlk 225 atlanır!)

**Gün 3-44:** Aynı şekilde devam eder, **duplicate YOK!**

### Nasıl çalışır?
- `message_history.json` dosyası her gönderimden sonra güncellenir
- Her şablon için gönderilen numaralar kaydedilir
- Bir sonraki gönderimdde bu numaralar otomatik atlanır

**Örnek `message_history.json`:**
```json
{
  "hello_world": [
    "905551234567",
    "905559876543",
    ...
  ],
  "order_confirmation": [
    "905551234567"
  ]
}
```

---

## 5️⃣ Test Edin

Uygulamanın çalıştığını test etmek için:

```bash
python test_api.py
```

Bu script şunları kontrol eder:
- ✅ Kişi listesi yükleniyor mu?
- ✅ Mesaj geçmişi çalışıyor mu?
- ✅ Webhook logları kaydediliyor mu?
- ✅ Duplicate kontrolü çalışıyor mu?

---

## 📊 Web Arayüzü Özellikleri

### Ana Sayfa (http://localhost:5005)

1. **📤 Mesaj Gönder Paneli:**
   - Şablon adı girin
   - Kişi sayısı seçin
   - Tek tıkla gönder

2. **📊 İstatistikler:**
   - Toplam kişi sayısı
   - Kullanılan şablon sayısı
   - Toplam gönderilen mesaj

3. **📝 Mesaj Geçmişi:**
   - Hangi şablondan kaç kişiye gönderildi?
   - Gerçek zamanlı güncelleme

4. **🔔 Webhook Logları:**
   - Mesaj durumları (sent, delivered, read, failed)
   - Otomatik yenileme (10 saniyede bir)

---

## ⚡ Hızlı Komutlar

```bash
# Uygulamayı başlat
python app.py

# Test et
python test_api.py

# Mesaj geçmişini göster
cat message_history.json | python -m json.tool

# Webhook loglarını göster (son 10)
cat webhook_logs.json | python -m json.tool | tail -n 20

# İstatistikleri API'den al
curl http://localhost:5005/api/history | python -m json.tool
```

---

## 🔒 Güvenlik Notları

✅ **YAPILMASI GEREKENLER:**
- `.env` dosyasını asla Git'e commit etmeyin
- `ACCESS_TOKEN` gizli tutun
- Production'da HTTPS kullanın

❌ **YAPILMAMASI GEREKENLER:**
- Token'ı kod içine yazmayın
- `.env` dosyasını paylaşmayın
- Test token'ı production'da kullanmayın

---

## 🆘 Sorun Giderme

### "Access token hatası" alıyorum
→ `.env` dosyasındaki `WHATSAPP_ACCESS_TOKEN` doğru mu kontrol edin
→ Token'ın süresi dolmuş olabilir, yeni token oluşturun

### "Template not found" hatası
→ Şablon adını Meta Business'ta kontrol edin
→ Şablonun onaylanmış olduğundan emin olun

### Webhook çalışmıyor
→ Ngrok tunnel'ının aktif olduğunu kontrol edin
→ Meta Console'da webhook URL'in güncel olduğunu kontrol edin

### Duplicate kontrolü çalışmıyor
→ `message_history.json` dosyasının yazma izni olduğundan emin olun
→ Dosya formatının doğru olduğunu kontrol edin

---

## 📞 Yardım

Sorularınız için:
- README.md dosyasını okuyun (detaylı bilgi)
- WhatsApp API Docs: https://developers.facebook.com/docs/whatsapp

---

## ✅ Başarılı Kullanım Örneği

```bash
# 1. Uygulamayı başlat
python app.py

# 2. Başka bir terminalde test et
python test_api.py

# 3. İlk 225 kişiye mesaj gönder
curl -X POST http://localhost:5005/api/send \
  -H "Content-Type: application/json" \
  -d '{"template_name": "hello_world", "limit": 225}'

# 4. Sonucu kontrol et
curl http://localhost:5005/api/history | python -m json.tool

# 5. Yarın aynı komutu tekrar çalıştır - duplicate olmayacak!
```

**Hepsi bu kadar! İyi kullanımlar! 🚀**
