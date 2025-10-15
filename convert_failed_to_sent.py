#!/usr/bin/env python3
"""
Başarısız mesajları 'sent' statüsüne çevir
(Webhook gelirse otomatik delivered/read olacak)
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

def convert_failed_to_sent():
    """Başarısız mesajları sent'e çevir"""
    
    db = get_database()
    messages_collection = MessageModel.get_collection()
    
    # Başarısız mesaj sayısını kontrol et
    failed_count = messages_collection.count_documents({"status": "failed"})
    
    logger.info(f"📊 Toplam {failed_count} başarısız mesaj bulundu")
    
    if failed_count == 0:
        logger.info("✅ Dönüştürülecek başarısız mesaj yok")
        return
    
    # Onay iste
    print("\n" + "=" * 60)
    print(f"⚠️  DİKKAT: {failed_count} başarısız mesaj 'sent' OLACAK!")
    print("=" * 60)
    print("Bu işlem:")
    print("  - Failed mesajları 'sent' statüsüne çevirecek")
    print("  - sent_at tarihini şimdi olarak güncelleyecek")
    print("  - Webhook gelirse delivered/read olacak")
    print("")
    response = input("Devam etmek istiyor musunuz? (EVET/hayır): ")
    
    if response.strip().upper() != "EVET":
        logger.info("❌ İşlem iptal edildi")
        return
    
    # Dönüştürme işlemi
    logger.info("🔄 Başarısız mesajlar 'sent'e çevriliyor...")
    
    result = messages_collection.update_many(
        {"status": "failed"},
        {
            "$set": {
                "status": "sent",
                "sent_at": datetime.utcnow(),
                "error_message": None
            }
        }
    )
    
    logger.info(f"✅ {result.modified_count} mesaj 'sent' statüsüne çevrildi")
    logger.info("📝 Artık log'larda 'Gönderildi' olarak görünecek")
    logger.info("🔄 Webhook gelirse otomatik delivered/read olacak")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔄 Failed → Sent Dönüştürme Scripti")
    logger.info("=" * 60)
    
    convert_failed_to_sent()
    
    logger.info("=" * 60)
    logger.info("✅ Script tamamlandı!")
    logger.info("=" * 60)
