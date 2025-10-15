#!/usr/bin/env python3
"""
Duplicate mesaj loglarını temizle
Aynı telefon + template için birden fazla kayıt varsa, en yenisini tut
"""

import os
import logging
from datetime import datetime

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
from models import MessageModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def remove_duplicate_logs():
    """Duplicate mesaj loglarını temizle"""
    
    db = get_database()
    messages_collection = MessageModel.get_collection()
    
    # Telefon + template'e göre grupla
    pipeline = [
        {
            "$match": {
                "status": {"$in": ["sent", "delivered", "read"]}  # Sadece başarılı mesajlar
            }
        },
        {
            "$group": {
                "_id": {
                    "phone": "$phone",
                    "template_name": "$template_name"
                },
                "count": {"$sum": 1},
                "messages": {"$push": {
                    "id": "$_id",
                    "sent_at": "$sent_at",
                    "status": "$status"
                }}
            }
        },
        {
            "$match": {
                "count": {"$gt": 1}  # Birden fazla kayıt olanlar
            }
        }
    ]
    
    duplicates = list(messages_collection.aggregate(pipeline))
    
    logger.info(f"📊 {len(duplicates)} duplicate grup bulundu")
    
    if len(duplicates) == 0:
        logger.info("✅ Temizlenecek duplicate yok")
        return
    
    # Her grup için detay göster
    total_to_delete = 0
    for dup in duplicates:
        phone = dup['_id']['phone']
        template = dup['_id']['template_name']
        count = dup['count']
        
        logger.info(f"\n📱 {phone} - {template}: {count} kayıt")
        
        # En yeni kayıt hariç diğerlerini göster
        messages = sorted(dup['messages'], key=lambda x: x['sent_at'], reverse=True)
        for i, msg in enumerate(messages):
            if i == 0:
                logger.info(f"   ✅ Tutulacak: {msg['sent_at']} - {msg['status']}")
            else:
                logger.info(f"   ❌ Silinecek: {msg['sent_at']} - {msg['status']}")
                total_to_delete += 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 ÖZET:")
    logger.info(f"   Duplicate gruplar: {len(duplicates)}")
    logger.info(f"   Silinecek kayıt: {total_to_delete}")
    logger.info(f"{'='*60}")
    
    # Onay iste
    print("")
    response = input("Duplicate kayıtları silmek istiyor musunuz? (EVET/hayır): ")
    
    if response.strip().upper() != "EVET":
        logger.info("❌ İşlem iptal edildi")
        return
    
    # Silme işlemi
    deleted_count = 0
    for dup in duplicates:
        # En yeni kayıt hariç diğerlerini sil
        messages = sorted(dup['messages'], key=lambda x: x['sent_at'], reverse=True)
        
        for i, msg in enumerate(messages):
            if i > 0:  # İlk (en yeni) kayıt hariç
                result = messages_collection.delete_one({"_id": msg['id']})
                if result.deleted_count > 0:
                    deleted_count += 1
    
    logger.info(f"\n✅ {deleted_count} duplicate kayıt silindi")
    logger.info(f"📝 Her telefon + template için sadece en yeni kayıt kaldı")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🗑️  Duplicate Log Temizleme Scripti")
    logger.info("=" * 60)
    
    remove_duplicate_logs()
    
    logger.info("=" * 60)
    logger.info("✅ Script tamamlandı!")
    logger.info("=" * 60)
