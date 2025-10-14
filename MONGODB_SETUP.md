# 🚀 MongoDB Entegrasyonu - Setup Rehberi

## 📋 Yapılacaklar Listesi

### 1. **MongoDB Kullanıcı ve Şifre Ayarla**

MongoDB Atlas Dashboard'a gidin:
```
https://cloud.mongodb.com/
```

**Database Access → Add New Database User:**
- Username: `your_username`
- Password: `your_strong_password`
- Database User Privileges: **Read and write to any database**

### 2. **Network Access Ayarla**

**Network Access → Add IP Address:**
- Railway için: **Allow Access from Anywhere** (0.0.0.0/0)
- Veya Railway IP'lerini ekleyin

### 3. **Connection String Güncelle**

`.env` dosyanızı düzenleyin:

```bash
MONGODB_URI=mongodb+srv://your_username:your_password@toptanci.dzmla0l.mongodb.net/?retryWrites=true&w=majority&appName=toptanci
```

**❌ Dikkat:**
- `<db_username>` → gerçek kullanıcı adınız
- `<db_password>` → gerçek şifreniz
- Şifrede özel karakterler varsa **URL encode** edin

### 4. **Railway Environment Variables**

Railway Dashboard → Variables:

```bash
MONGODB_URI=mongodb+srv://your_username:your_password@toptanci.dzmla0l.mongodb.net/?retryWrites=true&w=majority&appName=toptanci
```

### 5. **Bağımlılıkları Kur**

```bash
pip3 install --break-system-packages -r requirements.txt
```

### 6. **MongoDB'ye Migration Yap**

JSON verilerinizi MongoDB'ye aktarın:

```bash
python3 migrate_to_mongodb.py
```

**Göreceğiniz çıktı:**
```
🚀 MongoDB Migration Başlıyor...
✅ MongoDB bağlantısı: toptanci
📋 Kişiler migrate ediliyor...
✅ 150 kişi eklendi
📨 Mesaj geçmişi migrate ediliyor...
✅ 1200 mesaj kaydı eklendi
🔗 Webhook logları migrate ediliyor...
✅ 500 webhook log eklendi
✅ Migration tamamlandı!

📊 Veritabanı İstatistikleri:
   Kişiler: 150
   Mesajlar: 1200
   Webhook Logları: 500
```

## 📊 MongoDB Collections

### **contacts**
```json
{
  "phone": "905385524858",
  "name": "Ahmet Yılmaz",
  "country": "TR",
  "tags": ["vip", "customer"],
  "is_active": true,
  "created_at": "2025-10-14T10:30:00",
  "metadata": {}
}
```

### **messages**
```json
{
  "phone": "905385524858",
  "template_name": "sablon_tr",
  "message_type": "template",
  "status": "delivered",
  "message_id": "wamid.XXX",
  "sent_at": "2025-10-14T10:30:00",
  "delivered_at": "2025-10-14T10:30:05",
  "read_at": "2025-10-14T10:31:00"
}
```

### **campaigns**
```json
{
  "name": "Ocak Kampanyası",
  "template_name": "sablon_tr",
  "target_phones": ["905385524858", ...],
  "total_count": 150,
  "sent_count": 147,
  "delivered_count": 145,
  "failed_count": 2,
  "status": "completed"
}
```

### **webhook_logs**
```json
{
  "event_type": "status",
  "phone": "905385524858",
  "data": {...},
  "timestamp": "2025-10-14T10:30:00"
}
```

### **chats**
```json
{
  "phone": "905385524858",
  "direction": "incoming",
  "message_type": "text",
  "content": "Merhaba",
  "timestamp": "2025-10-14T10:30:00"
}
```

## 🔧 Test

### **MongoDB Bağlantı Testi:**
```bash
python3 -c "from database import get_database; db = get_database(); print(f'✅ Connected: {db.name}')"
```

### **Kişi Sayısı Kontrol:**
```bash
python3 -c "from models import ContactModel; print(f'Contacts: {ContactModel.get_collection().count_documents({})}')"
```

## 🚀 Yeni Özellikler

### **1. Duplicate Prevention (Gelişmiş)**
- Her gönderim MongoDB'ye kaydedilir
- `MessageModel.get_sent_phones()` ile daha önce gönderilenleri filtreler
- **%100 accurate** - JSON'a bağımlı değil

### **2. Real-time Stats**
- Kaç kişiye gönderildi (pending)
- Kaç kişiye ulaştı (delivered)
- Kaç kişi okudu (read)
- Kaç hata (failed)

### **3. Contact Management API**
```python
# Webhook'tan contact ekle
ContactModel.create_contact("905385524858", "Ahmet", "TR", ["customer"])

# Contact güncelle
ContactModel.update_contact("905385524858", {"tags": ["vip"]})

# Contact sil
ContactModel.delete_contact("905385524858")
```

### **4. Campaign Tracking**
- Kampanya oluştur
- İlerleme takip et
- Raporlama

### **5. Chat History**
- Tüm gelen/giden mesajlar kaydedilir
- Numaraya özel chat geçmişi
- Timeline view

## ⚠️ Önemli Notlar

1. **Migration sadece 1 kez çalıştırılmalı**
   - Duplikasyon olmaması için `phone` unique index var

2. **JSON dosyaları yedek olarak kalsın**
   - MongoDB'ye geçtikten sonra da silinmemeli

3. **Railway'de MONGODB_URI ekleyin**
   - Deployment sonrası servis başlamayacaktır

4. **Index'ler otomatik oluşturulur**
   - Performance için gerekli

## 🐛 Sorun Giderme

### **"ServerSelectionTimeoutError"**
→ MongoDB Atlas'ta **Network Access** ayarlarını kontrol edin (0.0.0.0/0)

### **"Authentication failed"**
→ Kullanıcı adı/şifre yanlış, MongoDB Atlas → Database Access kontrol edin

### **"Database does not exist"**
→ Normal, ilk migration'da otomatik oluşturulacak

## 📚 Sonraki Adımlar

1. ✅ MongoDB kurulumu ve migration
2. 🔄 app.py'yi MongoDB ile entegre et
3. 🎨 HTML'i modüler yap
4. 📊 Yeni dashboard - gerçek istatistikler
5. 💬 Chat interface
6. 📨 Webhook-based contact sync
