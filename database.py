"""
MongoDB Database Connection ve Configuration
"""
import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

class Database:
    """MongoDB bağlantı singleton sınıfı"""
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        """MongoDB'ye bağlan"""
        if self._client is not None:
            return self._db
        
        try:
            mongodb_uri = os.environ.get("MONGODB_URI")
            
            if not mongodb_uri:
                logger.error("❌ MONGODB_URI environment variable bulunamadı!")
                raise ValueError("MONGODB_URI gerekli")
            
            # MongoDB bağlantısı
            self._client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
            )
            
            # Bağlantı testi
            self._client.admin.command('ping')
            
            # Database seç (URI'den veya default)
            try:
                self._db = self._client.get_database()
            except:
                # URI'de database belirtilmemişse default kullan
                self._db = self._client.get_database('whatsapp_api')
            
            logger.info("✅ MongoDB bağlantısı başarılı")
            logger.info(f"📊 Database: {self._db.name}")
            
            return self._db
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ MongoDB bağlantı hatası: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Beklenmeyen hata: {e}")
            raise
    
    def get_db(self):
        """Database instance döndür"""
        if self._db is None:
            return self.connect()
        return self._db
    
    def close(self):
        """MongoDB bağlantısını kapat"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("🔒 MongoDB bağlantısı kapatıldı")

# Global database instance
db_instance = Database()

def get_database():
    """Database instance al"""
    return db_instance.get_db()
