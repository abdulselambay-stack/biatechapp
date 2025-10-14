# 🚀 Railway Deployment Talimatları

## 1. Railway'de Environment Variables Ayarlayın

Railway Dashboard → Variables bölümünde şu değişkenleri ekleyin:

```bash
WHATSAPP_ACCESS_TOKEN=EAAQiYHZApb4IBPlGPQPriAPzkCVMCP18vrclmIFZC9TZC4dJx9xR8xo4HIyDilUdBrv41VRlVru5fPyrti4clWvlzGY6MVjZA9pGDvX4UC01XwqBVyaelq8b8dyEsslB1tCbeqZArSY15ntrbYb4Abw71YknkGVJYmmCccHtlCMnKdpl2jYZBYGkjcJRdwdAZDZD

PHONE_NUMBER_ID=789162337618655
```

**Not:** `VERIFY_TOKEN` hardcoded olarak `technoglobal123` ayarlanmıştır.

## 2. WhatsApp Webhook Ayarları

Meta Developer Console → WhatsApp → Configuration bölümünde:

**Webhook URL:**
```
https://biatechapp-production.up.railway.app/webhook
```

**Verify Token:**
```
technoglobal123
```

**Subscribe to fields:**
- ✅ messages
- ✅ message_status

## 3. Test

### Health Check:
```bash
curl https://biatechapp-production.up.railway.app/
```

**Beklenen Yanıt:**
```json
{
  "status": "running",
  "service": "WhatsApp Cloud API",
  "webhook_url": "/webhook",
  "verify_token": "technoglobal123"
}
```

### Webhook Doğrulama:
Meta'dan "Verify and Save" butonuna tıkladığınızda Railway loglarında göreceksiniz:
```
🔍 Webhook Doğrulama İsteği:
   Mode: subscribe
   Token (gelen): technoglobal123
   Token (beklenen): technoglobal123
   Challenge: 1234567890
✅ Webhook doğrulandı.
```

## 4. Railway Logs

Webhook doğrulama sırasında hata alırsanız Railway logs'u kontrol edin:

```bash
railway logs
```

Ya da Railway Dashboard'dan "Deployments" → "View Logs"

## 5. Sorun Giderme

### ❌ "Couldn't validate the callback URL"

**Sebep 1:** Environment variables eksik
- Çözüm: Railway'de WHATSAPP_ACCESS_TOKEN ve PHONE_NUMBER_ID'yi ekleyin

**Sebep 2:** App çalışmıyor
- Çözüm: Railway logs'u kontrol edin, hata varsa düzeltin

**Sebep 3:** Port hatası
- Çözüm: Railway otomatik PORT environment variable sağlar, kod bunu kullanıyor

**Sebep 4:** Webhook endpoint erişilemiyor
- Çözüm: `https://biatechapp-production.up.railway.app/` açın, çalışıyor mu kontrol edin

### ✅ Doğrulama Başarılı

Log'da şunu göreceksiniz:
```
✅ Webhook doğrulandı.
```

Meta Console'da:
```
✅ Webhook verified successfully
```
