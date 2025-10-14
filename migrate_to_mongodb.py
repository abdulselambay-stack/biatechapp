"""
JSON Verilerini MongoDB'ye Migrate Etme Script'i
"""
import json
import os
import logging

# .env dosyasını manuel yükle (app.py'deki gibi)
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✅ .env dosyası yüklendi: {env_path}")
    else:
        print(f"⚠️ .env dosyası bulunamadı: {env_path}")

# .env'i yükle
load_env_file()

from database import get_database
from models import ContactModel, MessageModel, WebhookLogModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_json(filepath):
    """JSON dosyasını yükle"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def migrate_contacts():
    """contacts_with_index.json → MongoDB contacts (Batch Processing)"""
    logger.info("📋 Kişiler migrate ediliyor...")
    
    contacts_file = os.path.join(os.path.dirname(__file__), "contacts_with_index.json")
    data = load_json(contacts_file)
    
    if not data:
        logger.warning("⚠️ contacts_with_index.json bulunamadı veya boş")
        return
    
    # Dosya direkt array mi yoksa object mi kontrol et
    contact_list = data if isinstance(data, list) else data.get('contacts', [])
    
    if not contact_list:
        logger.warning("⚠️ Kişi verisi bulunamadı")
        return
    
    total_contacts = len(contact_list)
    logger.info(f"   Toplam {total_contacts} kişi bulundu")
    
    # Batch settings
    BATCH_SIZE = 500
    total_added = 0
    total_skipped = 0
    
    # Batch processing
    for i in range(0, total_contacts, BATCH_SIZE):
        batch = contact_list[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (total_contacts + BATCH_SIZE - 1) // BATCH_SIZE
        
        logger.info(f"   📦 Batch {batch_num}/{total_batches} işleniyor ({len(batch)} kişi)...")
        
        # Bu batch'teki tüm telefon numaralarını al
        batch_phones = []
        for contact in batch:
            phone = contact.get('phone') or contact.get('id')
            if phone:
                batch_phones.append(phone)
        
        # Mevcut numaraları toplu kontrol et (tek sorgu)
        existing_phones = set()
        if batch_phones:
            existing_contacts = ContactModel.get_collection().find(
                {"phone": {"$in": batch_phones}},
                {"phone": 1}
            )
            existing_phones = {c["phone"] for c in existing_contacts}
        
        # Yeni kişileri hazırla
        contacts = []
        skipped = 0
        
        for contact in batch:
            phone = contact.get('phone') or contact.get('id')
            
            if not phone:
                continue
            
            # Zaten var mı kontrol et (set lookup - O(1))
            if phone in existing_phones:
                skipped += 1
                continue
            
            # name veya pushname kullan
            name = contact.get('name') or contact.get('pushname') or phone
            
            contacts.append({
                "phone": phone,
                "name": name,
                "country": contact.get('country', ''),
                "tags": contact.get('tags', []),
                "metadata": {
                    "original_index": contact.get('index', 0),
                    "pushname": contact.get('pushname', '')
                }
            })
        
        # Bu batch'i MongoDB'ye ekle
        if contacts:
            try:
                count = ContactModel.bulk_create(contacts)
                total_added += count
                logger.info(f"      ✅ {count} yeni kişi eklendi")
            except Exception as e:
                logger.error(f"      ❌ Batch ekleme hatası: {e}")
                # Tek tek eklemeyi dene
                for contact in contacts:
                    try:
                        ContactModel.create_contact(
                            phone=contact["phone"],
                            name=contact["name"],
                            country=contact.get("country", ""),
                            tags=contact.get("tags", [])
                        )
                        total_added += 1
                    except:
                        pass
        
        if skipped > 0:
            total_skipped += skipped
            logger.info(f"      ⏭️ {skipped} kişi zaten mevcut")
        
        # Progress
        processed = min(i + BATCH_SIZE, total_contacts)
        progress_pct = (processed / total_contacts) * 100
        logger.info(f"      📊 İlerleme: {processed}/{total_contacts} ({progress_pct:.1f}%)")
        
        # Kısa pause (MongoDB'ye nefes aldır)
        import time
        time.sleep(0.1)
    
    logger.info(f"\n✅ Toplam {total_added} yeni kişi eklendi")
    if total_skipped > 0:
        logger.info(f"   ⏭️ Toplam {total_skipped} kişi zaten mevcuttu")

def migrate_message_history():
    """message_history.json → MongoDB messages"""
    logger.info("📨 Mesaj geçmişi migrate ediliyor...")
    
    history_file = os.path.join(os.path.dirname(__file__), "message_history.json")
    data = load_json(history_file)
    
    if not data:
        logger.warning("⚠️ message_history.json bulunamadı veya boş")
        return
    
    total = 0
    for template_name, phones in data.items():
        logger.info(f"   Template: {template_name} - {len(phones)} mesaj")
        
        for phone in phones:
            # Zaten kayıtlı mı kontrol et
            existing = MessageModel.get_collection().find_one({
                "phone": phone,
                "template_name": template_name
            })
            
            if not existing:
                MessageModel.create_message(
                    phone=phone,
                    template_name=template_name,
                    status="delivered",  # Geçmiş kayıtlar başarılı kabul ediliyor
                    message_type="template"
                )
                total += 1
    
    logger.info(f"✅ {total} mesaj kaydı eklendi")

def migrate_webhook_logs():
    """webhook_logs.json → MongoDB webhook_logs"""
    logger.info("🔗 Webhook logları migrate ediliyor...")
    
    logs_file = os.path.join(os.path.dirname(__file__), "webhook_logs.json")
    data = load_json(logs_file)
    
    if not data:
        logger.warning("⚠️ webhook_logs.json bulunamadı veya boş")
        return
    
    # Son 1000 log'u al (çok fazla eski log olabilir)
    recent_logs = data[-1000:] if len(data) > 1000 else data
    
    for log_entry in recent_logs:
        event_type = log_entry.get('type', 'unknown')
        phone = log_entry.get('from') or log_entry.get('recipient')
        
        WebhookLogModel.create_log(
            event_type=event_type,
            phone=phone,
            data=log_entry
        )
    
    logger.info(f"✅ {len(recent_logs)} webhook log eklendi")

def migrate_processed():
    """processed.json → MongoDB messages (duplicate tracking)"""
    logger.info("✅ İşlenmiş kayıtlar kontrol ediliyor...")
    
    processed_file = os.path.join(os.path.dirname(__file__), "processed.json")
    data = load_json(processed_file)
    
    if not data:
        logger.warning("⚠️ processed.json bulunamadı veya boş")
        return
    
    # processed.json'daki veriler zaten message_history'de olmalı
    # Sadece kontrol amaçlı
    for template_name, phones in data.items():
        count = MessageModel.get_collection().count_documents({
            "template_name": template_name,
            "phone": {"$in": phones}
        })
        logger.info(f"   {template_name}: {count}/{len(phones)} kayıt MongoDB'de")

def run_migration():
    """Tüm migration'ları çalıştır"""
    logger.info("=" * 60)
    logger.info("🚀 MongoDB Migration Başlıyor...")
    logger.info("=" * 60)
    
    try:
        # MongoDB bağlantısını test et
        db = get_database()
        logger.info(f"✅ MongoDB bağlantısı: {db.name}")
        
        # Index'leri oluştur
        logger.info("\n📊 Index'ler oluşturuluyor...")
        ContactModel.get_collection().create_index("phone", unique=True)
        MessageModel.get_collection().create_index([("phone", 1), ("template_name", 1)])
        MessageModel.get_collection().create_index("message_id")
        MessageModel.get_collection().create_index("status")
        WebhookLogModel.get_collection().create_index("timestamp")
        logger.info("✅ Index'ler oluşturuldu")
        
        # Migration'ları çalıştır
        logger.info("\n" + "=" * 60)
        migrate_contacts()
        
        logger.info("\n" + "=" * 60)
        migrate_message_history()
        
        logger.info("\n" + "=" * 60)
        migrate_webhook_logs()
        
        logger.info("\n" + "=" * 60)
        migrate_processed()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Migration tamamlandı!")
        logger.info("=" * 60)
        
        # İstatistikler
        logger.info("\n📊 Veritabanı İstatistikleri:")
        logger.info(f"   Kişiler: {ContactModel.get_collection().count_documents({})}")
        logger.info(f"   Mesajlar: {MessageModel.get_collection().count_documents({})}")
        logger.info(f"   Webhook Logları: {WebhookLogModel.get_collection().count_documents({})}")
        
    except Exception as e:
        logger.error(f"❌ Migration hatası: {e}")
        raise

if __name__ == "__main__":
    run_migration()
