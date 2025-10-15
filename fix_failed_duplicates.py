#!/usr/bin/env python3
"""
Başarısız mesajların sent_templates listesinden çıkarılması
- Failed durumundaki mesajlar için contact.sent_templates'den template ismini kaldır
- Böylece tekrar gönderilebilir hale gelir
"""

from database import get_database
from models import ContactModel, MessageModel
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_failed_duplicates():
    """Başarısız mesajları sent_templates'den çıkar"""
    
    db = get_database()
    messages_collection = MessageModel.get_collection()
    contacts_collection = ContactModel.get_collection()
    
    # Tüm başarısız mesajları bul
    failed_messages = list(messages_collection.find({
        "status": "failed"
    }))
    
    logger.info(f"📊 Toplam {len(failed_messages)} başarısız mesaj bulundu")
    
    fixed_count = 0
    
    for msg in failed_messages:
        phone = msg.get("phone")
        template_name = msg.get("template_name")
        
        if not phone or not template_name:
            continue
        
        # Contact'ı bul
        contact = contacts_collection.find_one({"phone": phone})
        
        if not contact:
            logger.warning(f"⚠️  Contact bulunamadı: {phone}")
            continue
        
        sent_templates = contact.get("sent_templates", [])
        
        # Template sent_templates'de varsa çıkar
        if template_name in sent_templates:
            contacts_collection.update_one(
                {"phone": phone},
                {"$pull": {"sent_templates": template_name}}
            )
            fixed_count += 1
            logger.info(f"✅ Fixed: {phone} - {template_name} removed from sent_templates")
    
    logger.info(f"🎉 Tamamlandı! {fixed_count} başarısız mesaj düzeltildi")
    logger.info(f"📝 Bu kişiler artık tekrar gönderim alabilir")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔧 Başarısız Mesaj Düzeltme Scripti")
    logger.info("=" * 60)
    
    fix_failed_duplicates()
    
    logger.info("=" * 60)
    logger.info("✅ Script tamamlandı!")
    logger.info("=" * 60)
