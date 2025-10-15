#!/usr/bin/env python3
"""
Başarısız mesajların sent_templates listesinden çıkarılması
- Failed durumundaki mesajlar için contact.sent_templates'den template ismini kaldır
- Böylece tekrar gönderilebilir hale gelir
"""

import os
import logging

# .env dosyasını manuel yükle
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        return True
    return False

# .env'yi yükle
if not load_env_file():
    print("⚠️  .env dosyası bulunamadı!")

from database import get_database
from models import ContactModel, MessageModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_failed_duplicates():
    """Başarısız mesajları sent_templates'den çıkar - BATCH UPDATE"""
    
    db = get_database()
    messages_collection = MessageModel.get_collection()
    contacts_collection = ContactModel.get_collection()
    
    # Tüm başarısız mesajları bul
    failed_messages = list(messages_collection.find({
        "status": "failed"
    }, {"phone": 1, "template_name": 1}))  # Sadece gerekli alanları çek
    
    logger.info(f"📊 Toplam {len(failed_messages)} başarısız mesaj bulundu")
    
    # Phone ve template_name ikililerini topla
    phone_template_pairs = {}
    for msg in failed_messages:
        phone = msg.get("phone")
        template_name = msg.get("template_name")
        
        if not phone or not template_name:
            continue
        
        if phone not in phone_template_pairs:
            phone_template_pairs[phone] = set()
        phone_template_pairs[phone].add(template_name)
    
    logger.info(f"📱 {len(phone_template_pairs)} benzersiz telefon numarası işlenecek")
    
    # BATCH UPDATE - Her telefon için bir kere update
    from pymongo import UpdateOne
    
    bulk_operations = []
    for phone, templates in phone_template_pairs.items():
        for template in templates:
            bulk_operations.append(
                UpdateOne(
                    {"phone": phone},
                    {"$pull": {"sent_templates": template}}
                )
            )
    
    if bulk_operations:
        logger.info(f"🚀 {len(bulk_operations)} batch update yapılıyor...")
        result = contacts_collection.bulk_write(bulk_operations, ordered=False)
        
        logger.info(f"✅ Matched: {result.matched_count}")
        logger.info(f"✅ Modified: {result.modified_count}")
    else:
        logger.info("⚠️  Güncellenecek kayıt yok")
    
    logger.info(f"🎉 Tamamlandı!")
    logger.info(f"📝 Bu kişiler artık tekrar gönderim alabilir")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔧 Başarısız Mesaj Düzeltme Scripti")
    logger.info("=" * 60)
    
    fix_failed_duplicates()
    
    logger.info("=" * 60)
    logger.info("✅ Script tamamlandı!")
    logger.info("=" * 60)
