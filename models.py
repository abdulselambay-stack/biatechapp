"""
MongoDB Collection Models ve Helper Functions
"""
from datetime import datetime
from typing import Dict, List, Optional
from pymongo.collection import Collection
from bson.objectid import ObjectId
from database import get_database

class ContactModel:
    """Kişi Yönetimi"""
    
    @staticmethod
    def get_collection() -> Collection:
        return get_database()['contacts']
    
    @staticmethod
    def create_contact(phone: str, name: str, country: str = "", tags: List[str] = None) -> Dict:
        """Yeni kişi ekle"""
        contact = {
            "phone": phone,
            "name": name,
            "country": country,
            "tags": tags or [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "metadata": {}
        }
        
        result = ContactModel.get_collection().insert_one(contact)
        contact['_id'] = str(result.inserted_id)
        return contact
    
    @staticmethod
    def get_contact(phone: str) -> Optional[Dict]:
        """Telefon numarasına göre kişi getir"""
        contact = ContactModel.get_collection().find_one({"phone": phone})
        if contact:
            contact['_id'] = str(contact['_id'])
        return contact
    
    @staticmethod
    def get_all_contacts(tags: List[str] = None, is_active: bool = True) -> List[Dict]:
        """Tüm kişileri getir (filtreleme ile)"""
        query = {"is_active": is_active}
        if tags:
            query["tags"] = {"$in": tags}
        
        contacts = list(ContactModel.get_collection().find(query))
        for contact in contacts:
            contact['_id'] = str(contact['_id'])
        return contacts
    
    @staticmethod
    def update_contact(phone: str, updates: Dict) -> bool:
        """Kişi güncelle"""
        updates['updated_at'] = datetime.utcnow()
        result = ContactModel.get_collection().update_one(
            {"phone": phone},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete_contact(phone: str) -> bool:
        """Kişi sil (soft delete)"""
        return ContactModel.update_contact(phone, {"is_active": False})
    
    @staticmethod
    def bulk_create(contacts: List[Dict]) -> int:
        """Toplu kişi ekleme"""
        for contact in contacts:
            contact['created_at'] = datetime.utcnow()
            contact['updated_at'] = datetime.utcnow()
            contact['is_active'] = contact.get('is_active', True)
            contact['tags'] = contact.get('tags', [])
            contact['metadata'] = contact.get('metadata', {})
        
        result = ContactModel.get_collection().insert_many(contacts)
        return len(result.inserted_ids)


class MessageModel:
    """Mesaj Gönderim Takibi"""
    
    @staticmethod
    def get_collection() -> Collection:
        return get_database()['messages']
    
    @staticmethod
    def create_message(
        phone: str,
        template_name: str,
        message_type: str = "template",
        content: str = "",
        media_url: str = None,
        status: str = "pending"
    ) -> Dict:
        """Yeni mesaj kaydı oluştur"""
        message = {
            "phone": phone,
            "template_name": template_name,
            "message_type": message_type,
            "content": content,
            "media_url": media_url,
            "status": status,
            "message_id": None,  # WhatsApp'tan gelecek
            "sent_at": datetime.utcnow(),
            "delivered_at": None,
            "read_at": None,
            "failed_at": None,
            "error_message": None,
            "metadata": {}
        }
        
        result = MessageModel.get_collection().insert_one(message)
        message['_id'] = str(result.inserted_id)
        return message
    
    @staticmethod
    def update_status(message_id: str, status: str, error: str = None):
        """Mesaj durumunu güncelle (WhatsApp webhook'tan)"""
        updates = {"status": status}
        
        if status == "delivered":
            updates["delivered_at"] = datetime.utcnow()
        elif status == "read":
            updates["read_at"] = datetime.utcnow()
        elif status == "failed":
            updates["failed_at"] = datetime.utcnow()
            updates["error_message"] = error
        
        MessageModel.get_collection().update_one(
            {"message_id": message_id},
            {"$set": updates}
        )
    
    @staticmethod
    def set_message_id(phone: str, template_name: str, message_id: str):
        """WhatsApp message ID'yi kaydet"""
        MessageModel.get_collection().update_one(
            {"phone": phone, "template_name": template_name, "message_id": None},
            {"$set": {"message_id": message_id}},
            upsert=False
        )
    
    @staticmethod
    def get_sent_phones(template_name: str) -> List[str]:
        """Bu template'e daha önce mesaj gönderilen numaraları getir"""
        messages = MessageModel.get_collection().find(
            {"template_name": template_name, "status": {"$in": ["sent", "delivered", "read"]}},
            {"phone": 1}
        )
        return [msg["phone"] for msg in messages]
    
    @staticmethod
    def get_stats(template_name: str = None) -> Dict:
        """Mesaj istatistikleri"""
        query = {}
        if template_name:
            query["template_name"] = template_name
        
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        results = list(MessageModel.get_collection().aggregate(pipeline))
        stats = {result["_id"]: result["count"] for result in results}
        
        return {
            "total": sum(stats.values()),
            "sent": stats.get("sent", 0) + stats.get("delivered", 0) + stats.get("read", 0),
            "delivered": stats.get("delivered", 0),
            "read": stats.get("read", 0),
            "failed": stats.get("failed", 0),
            "pending": stats.get("pending", 0)
        }


class CampaignModel:
    """Kampanya Yönetimi"""
    
    @staticmethod
    def get_collection() -> Collection:
        return get_database()['campaigns']
    
    @staticmethod
    def create_campaign(
        name: str,
        template_name: str,
        target_phones: List[str],
        scheduled_at: datetime = None
    ) -> Dict:
        """Yeni kampanya oluştur"""
        campaign = {
            "name": name,
            "template_name": template_name,
            "target_phones": target_phones,
            "total_count": len(target_phones),
            "sent_count": 0,
            "delivered_count": 0,
            "failed_count": 0,
            "status": "scheduled" if scheduled_at else "pending",
            "scheduled_at": scheduled_at,
            "started_at": None,
            "completed_at": None,
            "created_at": datetime.utcnow(),
            "is_running": False
        }
        
        result = CampaignModel.get_collection().insert_one(campaign)
        campaign['_id'] = str(result.inserted_id)
        return campaign
    
    @staticmethod
    def update_progress(campaign_id: str, sent: int, delivered: int, failed: int):
        """Kampanya ilerlemesini güncelle"""
        CampaignModel.get_collection().update_one(
            {"_id": campaign_id},
            {"$set": {
                "sent_count": sent,
                "delivered_count": delivered,
                "failed_count": failed
            }}
        )


class WebhookLogModel:
    """Webhook Log Kayıtları"""
    
    @staticmethod
    def get_collection() -> Collection:
        return get_database()['webhook_logs']
    
    @staticmethod
    def create_log(event_type: str, data: Dict, phone: str = None) -> Dict:
        """Webhook log kaydet"""
        log = {
            "event_type": event_type,
            "phone": phone,
            "data": data,
            "timestamp": datetime.utcnow()
        }
        
        result = WebhookLogModel.get_collection().insert_one(log)
        log['_id'] = str(result.inserted_id)
        return log
    
    @staticmethod
    def get_recent_logs(limit: int = 100) -> List[Dict]:
        """Son webhook loglarını getir"""
        logs = list(WebhookLogModel.get_collection()
                   .find()
                   .sort("timestamp", -1)
                   .limit(limit))
        
        for log in logs:
            log['_id'] = str(log['_id'])
            log['timestamp'] = log['timestamp'].isoformat()
        
        return logs


class ChatModel:
    """Chat Geçmişi"""
    
    @staticmethod
    def get_collection() -> Collection:
        return get_database()['chats']
    
    @staticmethod
    def save_message(phone: str, direction: str, message_type: str, content: str, media_url: str = None):
        """Chat mesajı kaydet (gelen/giden)"""
        message = {
            "phone": phone,
            "direction": direction,  # "incoming" veya "outgoing"
            "message_type": message_type,  # "text", "image", "video", etc
            "content": content,
            "media_url": media_url,
            "timestamp": datetime.utcnow()
        }
        
        ChatModel.get_collection().insert_one(message)
    
    @staticmethod
    def get_chat_history(phone: str, limit: int = 100) -> List[Dict]:
        """Bir numarayla olan chat geçmişini getir"""
        chats = list(ChatModel.get_collection()
                    .find({"phone": phone})
                    .sort("timestamp", -1)
                    .limit(limit))
        
        for chat in chats:
            chat['_id'] = str(chat['_id'])
            chat['timestamp'] = chat['timestamp'].isoformat()
        
        return list(reversed(chats))  # Eskiden yeniye sırala
    
    @staticmethod
    def get_all_chats() -> List[Dict]:
        """Tüm chat'leri telefon numarasına göre grupla"""
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$phone",
                "last_message": {"$first": "$content"},
                "last_message_time": {"$first": "$timestamp"},
                "message_count": {"$sum": 1}
            }},
            {"$sort": {"last_message_time": -1}}
        ]
        
        chats = list(ChatModel.get_collection().aggregate(pipeline))
        
        for chat in chats:
            chat['phone'] = chat.pop('_id')
            chat['last_message_time'] = chat['last_message_time'].isoformat()
        
        return chats

class SalesModel:
    """Satış Takip Sistemi"""
    
    @staticmethod
    def get_collection() -> Collection:
        return get_database()['sales']
    
    @staticmethod
    def create_sale(phone: str, customer_name: str, amount: float, profit: float, 
                    currency: str = "USD", product: str = "", notes: str = "") -> Dict:
        """Yeni satış kaydı oluştur"""
        sale = {
            "phone": phone,
            "customer_name": customer_name,
            "amount": float(amount),  # Toplam satış tutarı
            "profit": float(profit),   # Kar
            "currency": currency,
            "product": product,
            "notes": notes,
            "sale_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "status": "completed"  # completed, pending, cancelled
        }
        
        result = SalesModel.get_collection().insert_one(sale)
        sale['_id'] = str(result.inserted_id)
        
        # Contact'a satış flag'i ekle
        ContactModel.get_collection().update_one(
            {"phone": phone},
            {
                "$set": {"has_sale": True, "last_sale_date": datetime.utcnow()},
                "$inc": {"total_sales": 1}
            }
        )
        
        return sale
    
    @staticmethod
    def get_all_sales(limit: int = 100, skip: int = 0) -> List[Dict]:
        """Tüm satışları getir"""
        sales = list(SalesModel.get_collection()
                    .find()
                    .sort("sale_date", -1)
                    .skip(skip)
                    .limit(limit))
        
        for sale in sales:
            sale['_id'] = str(sale['_id'])
            sale['sale_date'] = sale['sale_date'].isoformat()
            sale['created_at'] = sale['created_at'].isoformat()
        
        return sales
    
    @staticmethod
    def get_sales_by_phone(phone: str) -> List[Dict]:
        """Bir kişinin tüm satışlarını getir"""
        sales = list(SalesModel.get_collection()
                    .find({"phone": phone})
                    .sort("sale_date", -1))
        
        for sale in sales:
            sale['_id'] = str(sale['_id'])
            sale['sale_date'] = sale['sale_date'].isoformat()
            sale['created_at'] = sale['created_at'].isoformat()
        
        return sales
    
    @staticmethod
    def get_sales_stats() -> Dict:
        """Satış istatistikleri"""
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_sales": {"$sum": 1},
                    "total_amount": {"$sum": "$amount"},
                    "total_profit": {"$sum": "$profit"},
                    "avg_sale": {"$avg": "$amount"},
                    "avg_profit": {"$avg": "$profit"}
                }
            }
        ]
        
        result = list(SalesModel.get_collection().aggregate(pipeline))
        
        if result:
            stats = result[0]
            stats.pop('_id')
            return stats
        
        return {
            "total_sales": 0,
            "total_amount": 0,
            "total_profit": 0,
            "avg_sale": 0,
            "avg_profit": 0
        }
    
    @staticmethod
    def get_top_customers(limit: int = 10) -> List[Dict]:
        """En çok satış yapılan müşteriler"""
        pipeline = [
            {
                "$group": {
                    "_id": "$phone",
                    "customer_name": {"$first": "$customer_name"},
                    "total_sales": {"$sum": 1},
                    "total_amount": {"$sum": "$amount"},
                    "total_profit": {"$sum": "$profit"},
                    "last_sale": {"$max": "$sale_date"}
                }
            },
            {"$sort": {"total_amount": -1}},
            {"$limit": limit}
        ]
        
        customers = list(SalesModel.get_collection().aggregate(pipeline))
        
        for customer in customers:
            customer['phone'] = customer.pop('_id')
            customer['last_sale'] = customer['last_sale'].isoformat()
        
        return customers
    
    @staticmethod
    def update_sale(sale_id: str, data: Dict) -> bool:
        """Satış güncelle"""
        try:
            result = SalesModel.get_collection().update_one(
                {"_id": ObjectId(sale_id)},
                {"$set": data}
            )
            return result.modified_count > 0
        except:
            return False
    
    @staticmethod
    def delete_sale(sale_id: str) -> bool:
        """Satış sil"""
        try:
            result = SalesModel.get_collection().delete_one({"_id": ObjectId(sale_id)})
            return result.deleted_count > 0
        except:
            return False
