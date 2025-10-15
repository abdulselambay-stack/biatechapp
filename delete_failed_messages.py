#!/usr/bin/env python3
"""
Başarısız mesajları database'den tamamen sil
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
from models import MessageModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def delete_failed_messages():
    """Tüm başarısız mesajları sil"""
    
    db = get_database()
    messages_collection = MessageModel.get_collection()
    
    # Başarısız mesaj sayısını kontrol et
    failed_count = messages_collection.count_documents({"status": "failed"})
    
    logger.info(f"📊 Toplam {failed_count} başarısız mesaj bulundu")
    
    if failed_count == 0:
        logger.info("✅ Silinecek başarısız mesaj yok")
        return
    
    # Onay iste
    print("\n" + "=" * 60)
    print(f"⚠️  DİKKAT: {failed_count} başarısız mesaj SİLİNECEK!")
    print("=" * 60)
    print("Bu işlem geri alınamaz. Log kayıtları tamamen silinecek.")
    print("")
    response = input("Devam etmek istiyor musunuz? (EVET/hayır): ")
    
    if response.strip().upper() != "EVET":
        logger.info("❌ İşlem iptal edildi")
        return
    
    # Silme işlemi
    logger.info("🗑️  Başarısız mesajlar siliniyor...")
    result = messages_collection.delete_many({"status": "failed"})
    
    logger.info(f"✅ {result.deleted_count} başarısız mesaj silindi")
    logger.info("📝 Artık log'larda görünmeyecek")
    logger.info("🔄 Başarısız olan numaralar tekrar gönderim alabilir")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🗑️  Başarısız Mesaj Silme Scripti")
    logger.info("=" * 60)
    
    delete_failed_messages()
    
    logger.info("=" * 60)
    logger.info("✅ Script tamamlandı!")
    logger.info("=" * 60)
