#!/usr/bin/env python3
"""
Meta Analytics API'den veri çek ve database ile karşılaştır
"""

import os
import requests
import logging
from datetime import datetime, timedelta

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

# Meta API credentials
WHATSAPP_BUSINESS_ID = os.environ.get("WHATSAPP_BUSINESS_ID")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

def get_meta_analytics():
    """Meta Analytics API'den veri çek"""
    
    # Son 30 günün istatistikleri
    url = f"https://graph.facebook.com/v24.0/{WHATSAPP_BUSINESS_ID}"
    
    # Conversation analytics endpoint
    analytics_url = f"{url}/conversation_analytics"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    
    # Son 30 gün
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    params = {
        "start": int(start_date.timestamp()),
        "end": int(end_date.timestamp()),
        "granularity": "DAILY",
        "conversation_type": ["REGULAR", "MARKETING", "UTILITY", "AUTHENTICATION", "SERVICE"],
        "conversation_direction": ["BUSINESS_INITIATED"]
    }
    
    try:
        logger.info("📊 Meta Analytics API'den veri çekiliyor...")
        response = requests.get(analytics_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Meta API Response: {data}")
            return data
        else:
            logger.error(f"❌ Meta API Error: {response.status_code}")
            logger.error(f"   Response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ API Error: {e}")
        return None

def get_database_stats():
    """Database'den istatistikleri çek"""
    
    db = get_database()
    messages_collection = MessageModel.get_collection()
    
    # Son 30 gün
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Status'lere göre say
    stats = {
        "sent": messages_collection.count_documents({
            "sent_at": {"$gte": thirty_days_ago},
            "status": "sent"
        }),
        "delivered": messages_collection.count_documents({
            "sent_at": {"$gte": thirty_days_ago},
            "status": "delivered"
        }),
        "read": messages_collection.count_documents({
            "sent_at": {"$gte": thirty_days_ago},
            "status": "read"
        }),
        "failed": messages_collection.count_documents({
            "sent_at": {"$gte": thirty_days_ago},
            "status": "failed"
        })
    }
    
    stats["total"] = stats["sent"] + stats["delivered"] + stats["read"]
    stats["total_with_failed"] = stats["total"] + stats["failed"]
    
    return stats

def compare_stats():
    """Meta ve Database verilerini karşılaştır"""
    
    logger.info("=" * 80)
    logger.info("📊 META vs DATABASE Karşılaştırması (Son 30 Gün)")
    logger.info("=" * 80)
    
    # Database stats
    db_stats = get_database_stats()
    
    logger.info("\n📱 DATABASE İstatistikleri:")
    logger.info(f"   Sent:      {db_stats['sent']}")
    logger.info(f"   Delivered: {db_stats['delivered']}")
    logger.info(f"   Read:      {db_stats['read']}")
    logger.info(f"   Failed:    {db_stats['failed']}")
    logger.info(f"   ─────────────────────")
    logger.info(f"   TOPLAM:    {db_stats['total']} (başarılı)")
    logger.info(f"   TOPLAM:    {db_stats['total_with_failed']} (failed dahil)")
    
    # Meta stats
    logger.info("\n🌐 META Analytics:")
    meta_data = get_meta_analytics()
    
    if meta_data:
        logger.info("   ✅ Veri çekildi!")
        logger.info(f"   Data: {meta_data}")
    else:
        logger.warning("   ⚠️  Meta API verisi çekilemedi")
        logger.info("\n💡 Alternatif: Meta Business Suite'den manuel kontrol:")
        logger.info("   1. https://business.facebook.com/wa/manage/home/ adresine git")
        logger.info("   2. 'Insights' sekmesine tıkla")
        logger.info("   3. Son 30 gün verilerini kontrol et")
    
    logger.info("\n" + "=" * 80)
    logger.info("📋 ÖZET:")
    logger.info(f"   Database'de {db_stats['total']} başarılı mesaj var (son 30 gün)")
    logger.info(f"   Meta'da görünen sayı ile karşılaştırın")
    logger.info("=" * 80)

if __name__ == "__main__":
    logger.info("🔄 Meta Analytics Senkronizasyon")
    logger.info("=" * 80)
    
    compare_stats()
