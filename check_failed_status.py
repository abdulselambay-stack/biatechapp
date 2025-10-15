#!/usr/bin/env python3
"""
Başarısız mesajların durumunu kontrol et
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

load_env_file()

from database import get_database
from models import ContactModel, MessageModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_status():
    """Failed mesajların durumunu kontrol et"""
    
    db = get_database()
    messages_collection = MessageModel.get_collection()
    contacts_collection = ContactModel.get_collection()
    
    # Rastgele 10 başarısız mesaj al
    failed_messages = list(messages_collection.find({
        "status": "failed"
    }).limit(10))
    
    logger.info(f"📊 İlk 10 başarısız mesaj kontrol ediliyor...")
    logger.info("=" * 80)
    
    for i, msg in enumerate(failed_messages, 1):
        phone = msg.get("phone")
        template_name = msg.get("template_name")
        
        # Contact'ı bul
        contact = contacts_collection.find_one({"phone": phone})
        
        if contact:
            sent_templates = contact.get("sent_templates", [])
            in_list = template_name in sent_templates
            
            logger.info(f"\n[{i}] Phone: {phone}")
            logger.info(f"    Template: {template_name}")
            logger.info(f"    sent_templates'de: {'✅ VAR (PROBLEM!)' if in_list else '❌ YOK (Normal)'}")
            logger.info(f"    sent_templates: {sent_templates}")
        else:
            logger.warning(f"\n[{i}] Contact bulunamadı: {phone}")
    
    logger.info("=" * 80)
    
    # Özet istatistik
    all_failed = list(messages_collection.find({"status": "failed"}, {"phone": 1, "template_name": 1}))
    
    problem_count = 0
    for msg in all_failed:
        phone = msg.get("phone")
        template_name = msg.get("template_name")
        
        contact = contacts_collection.find_one({"phone": phone}, {"sent_templates": 1})
        if contact and template_name in contact.get("sent_templates", []):
            problem_count += 1
    
    logger.info(f"\n📊 ÖZET:")
    logger.info(f"   Toplam başarısız mesaj: {len(all_failed)}")
    logger.info(f"   sent_templates'de olan: {problem_count} (PROBLEM!)")
    logger.info(f"   sent_templates'de olmayan: {len(all_failed) - problem_count} (Normal)")
    
    if problem_count == 0:
        logger.info(f"\n✅ HİÇ PROBLEM YOK!")
        logger.info(f"   Başarısız mesajlar zaten sent_templates'de değil")
        logger.info(f"   Tekrar gönderim yapılabilir!")
    else:
        logger.warning(f"\n⚠️ {problem_count} mesajda problem var!")
        logger.warning(f"   Bu mesajlar sent_templates'den çıkarılmalı")

if __name__ == "__main__":
    logger.info("🔍 Başarısız Mesaj Durum Kontrolü")
    logger.info("=" * 80)
    check_status()
