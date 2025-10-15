"""
MongoDB Collection Models ve Helper Functions
"""
from datetime import datetime
from typing import Dict, List, Optional
from pymongo.collection import Collection
from bson.objectid import ObjectId
from database import get_database
import hashlib

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
            "sent_templates": [],  # Gönderilen template'ler
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
            contact['sent_templates'] = contact.get('sent_templates', [])
            contact['metadata'] = contact.get('metadata', {})
        
        result = ContactModel.get_collection().insert_many(contacts)
        return len(result.inserted_ids)
    
    @staticmethod
    def add_sent_template(phone: str, template_name: str) -> bool:
        """Kişiye gönderilen template'i ekle"""
        result = ContactModel.get_collection().update_one(
            {"phone": phone},
            {
                "$addToSet": {"sent_templates": template_name},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def has_received_template(phone: str, template_name: str) -> bool:
        """Kişi bu template'i daha önce aldı mı?"""
        contact = ContactModel.get_collection().find_one(
            {"phone": phone, "sent_templates": template_name}
        )
        return contact is not None
    
    @staticmethod
    def get_contacts_without_template(template_name: str, tags: List[str] = None) -> List[Dict]:
        """Belirli template'i almamış kişileri getir"""
        query = {
            "is_active": True,
            "sent_templates": {"$ne": template_name}
        }
        if tags:
            query["tags"] = {"$in": tags}
        
        contacts = list(ContactModel.get_collection().find(query))
        for contact in contacts:
            contact['_id'] = str(contact['_id'])
        return contacts


class TemplateSettingsModel:
    """Template ayarları (image ID, vb.)"""
    
    @staticmethod
    def get_collection() -> Collection:
        return get_database()['template_settings']
    
    @staticmethod
    def get_template_settings(template_name: str) -> Optional[Dict]:
        """Template ayarlarını getir"""
        settings = TemplateSettingsModel.get_collection().find_one({"template_name": template_name})
        if settings:
            settings['_id'] = str(settings['_id'])
        return settings
    
    @staticmethod
    def set_header_image_id(template_name: str, image_id: str) -> bool:
        """Template için header image ID kaydet"""
        result = TemplateSettingsModel.get_collection().update_one(
            {"template_name": template_name},
            {
                "$set": {
                    "template_name": template_name,
                    "header_image_id": image_id,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    
    @staticmethod
    def get_header_image_id(template_name: str) -> Optional[str]:
        """Template için kaydedilmiş image ID'yi getir"""
        settings = TemplateSettingsModel.get_template_settings(template_name)
        return settings.get("header_image_id") if settings else None


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
        status: str = "pending",
        error_message: str = None
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
            "failed_at": datetime.utcnow() if status == "failed" else None,
            "error_message": error_message,
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
            "is_read": direction == "outgoing",  # Giden mesajlar otomatik okunmuş
            "timestamp": datetime.utcnow()
        }
        
        result = ChatModel.get_collection().insert_one(message)
        return result.inserted_id
    
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
    def get_all_chats(filter_type: str = "all") -> List[Dict]:
        """
        Tüm chat'leri telefon numarasına göre grupla
        
        filter_type:
        - "all": Tüm konuşmalar
        - "incoming": Bize mesaj atanlar (incoming message var)
        - "unread": Okunmayanlar (last message incoming ve unread)
        - "replied": Bizim cevap verdiklerimiz (incoming + outgoing var)
        """
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$phone",
                "last_message": {"$first": "$content"},
                "last_message_time": {"$first": "$timestamp"},
                "last_message_direction": {"$first": "$direction"},
                "message_count": {"$sum": 1},
                "unread_count": {
                    "$sum": {
                        "$cond": [
                            {"$and": [
                                {"$eq": ["$direction", "incoming"]},
                                {"$eq": ["$is_read", False]}
                            ]},
                            1,
                            0
                        ]
                    }
                },
                "incoming_count": {
                    "$sum": {"$cond": [{"$eq": ["$direction", "incoming"]}, 1, 0]}
                },
                "outgoing_count": {
                    "$sum": {"$cond": [{"$eq": ["$direction", "outgoing"]}, 1, 0]}
                },
                "has_bulk_send": {
                    "$max": {"$cond": [{"$eq": ["$message_type", "template"]}, True, False]}
                }
            }},
            {"$sort": {"last_message_time": -1}}
        ]
        
        chats = list(ChatModel.get_collection().aggregate(pipeline))
        
        # Filtreleme uygula
        filtered_chats = []
        for chat in chats:
            chat['phone'] = chat.pop('_id')
            chat['last_message_time'] = chat['last_message_time'].isoformat()
            chat['has_replied'] = chat['incoming_count'] > 0 and chat['outgoing_count'] > 0
            
            # Filtre kontrolü
            if filter_type == "all":
                filtered_chats.append(chat)
            elif filter_type == "incoming" and chat['incoming_count'] > 0:
                filtered_chats.append(chat)
            elif filter_type == "unread" and chat['unread_count'] > 0:
                filtered_chats.append(chat)
            elif filter_type == "replied" and chat['has_replied']:
                filtered_chats.append(chat)
        
        return filtered_chats
    
    @staticmethod
    def mark_messages_as_read(phone: str):
        """Bir telefon numarasının tüm okunmamış mesajlarını okundu olarak işaretle"""
        ChatModel.get_collection().update_many(
            {
                "phone": phone,
                "direction": "incoming",
                "is_read": False
            },
            {"$set": {"is_read": True}}
        )
    
    @staticmethod
    def get_unread_count(phone: str = None) -> int:
        """Okunmamış mesaj sayısını getir"""
        query = {
            "direction": "incoming",
            "is_read": False
        }
        
        if phone:
            query["phone"] = phone
        
        return ChatModel.get_collection().count_documents(query)
    
    @staticmethod
    def get_total_unread_count() -> int:
        """Toplam okunmamış mesaj sayısı"""
        return ChatModel.get_unread_count()

class ProductModel:
    """Ürün Yönetimi"""
    
    @staticmethod
    def get_collection() -> Collection:
        return get_database()['products']
    
    @staticmethod
    def create_product(name: str, cost_price: float, sale_price: float, 
                       description: str = "", category: str = "", currency: str = "TRY") -> Dict:
        """Yeni ürün oluştur"""
        profit = float(sale_price) - float(cost_price)
        profit_margin = (profit / float(sale_price) * 100) if sale_price > 0 else 0
        
        product = {
            "name": name,
            "cost_price": float(cost_price),  # Geliş fiyatı
            "sale_price": float(sale_price),  # Satış fiyatı
            "profit": profit,  # Kar
            "profit_margin": round(profit_margin, 2),  # Kar marjı %
            "currency": currency,  # TRY veya USD
            "description": description,
            "category": category,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = ProductModel.get_collection().insert_one(product)
        product['_id'] = str(result.inserted_id)
        return product
    
    @staticmethod
    def get_all_products(active_only: bool = True) -> List[Dict]:
        """Tüm ürünleri getir"""
        query = {"is_active": True} if active_only else {}
        products = list(ProductModel.get_collection()
                       .find(query)
                       .sort("name", 1))
        
        for product in products:
            product['_id'] = str(product['_id'])
            product['created_at'] = product['created_at'].isoformat()
            product['updated_at'] = product['updated_at'].isoformat()
        
        return products
    
    @staticmethod
    def get_product_by_id(product_id: str) -> Dict:
        """Ürün ID'ye göre getir"""
        from bson import ObjectId
        product = ProductModel.get_collection().find_one({"_id": ObjectId(product_id)})
        
        if product:
            product['_id'] = str(product['_id'])
            product['created_at'] = product['created_at'].isoformat()
            product['updated_at'] = product['updated_at'].isoformat()
        
        return product
    
    @staticmethod
    def update_product(product_id: str, name: str, cost_price: float, 
                       sale_price: float, description: str = "", 
                       category: str = "", currency: str = "TRY") -> bool:
        """Ürün güncelle"""
        from bson import ObjectId
        
        profit = float(sale_price) - float(cost_price)
        profit_margin = (profit / float(sale_price) * 100) if sale_price > 0 else 0
        
        result = ProductModel.get_collection().update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {
                "name": name,
                "cost_price": float(cost_price),
                "sale_price": float(sale_price),
                "profit": profit,
                "profit_margin": round(profit_margin, 2),
                "currency": currency,
                "description": description,
                "category": category,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def delete_product(product_id: str) -> bool:
        """Ürünü sil (soft delete)"""
        from bson import ObjectId
        result = ProductModel.get_collection().update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0


class SalesModel:
    """Satış Takip Sistemi"""
    
    @staticmethod
    def get_collection() -> Collection:
        return get_database()['sales']
    
    @staticmethod
    def create_sale(phone: str, customer_name: str, product_id: str, 
                    quantity: int = 1, notes: str = "", currency: str = "TRY") -> Dict:
        """Yeni satış kaydı oluştur (ürün bazlı)"""
        from bson import ObjectId
        
        # Ürün bilgisini çek
        product = ProductModel.get_product_by_id(product_id)
        
        if not product:
            raise ValueError("Ürün bulunamadı")
        
        # Hesaplamalar
        total_cost = product['cost_price'] * quantity
        total_sale = product['sale_price'] * quantity
        total_profit = total_sale - total_cost
        
        sale = {
            "phone": phone,
            "customer_name": customer_name,
            "product_id": product_id,
            "product_name": product['name'],
            "quantity": quantity,
            "unit_cost_price": product['cost_price'],
            "unit_sale_price": product['sale_price'],
            "total_cost": round(total_cost, 2),
            "total_amount": round(total_sale, 2),  # Toplam satış tutarı
            "total_profit": round(total_profit, 2),   # Kar
            "profit_margin": product['profit_margin'],
            "currency": currency,
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

class AdminModel:
    """Admin Kullanıcı Yönetimi"""
    
    @staticmethod
    def get_collection() -> Collection:
        return get_database()['admins']
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Şifreyi hashle"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def create_default_admin():
        """Varsayılan admin kullanıcısı oluştur (uygulama başlangıcında)"""
        admin_exists = AdminModel.get_collection().find_one({"username": "admin"})
        
        if not admin_exists:
            admin = {
                "username": "admin",
                "password": AdminModel.hash_password("abdulselam"),
                "created_at": datetime.utcnow(),
                "is_active": True
            }
            AdminModel.get_collection().insert_one(admin)
            print("✅ Default admin user created (username: admin)")
        else:
            print("ℹ️  Admin user already exists")
    
    @staticmethod
    def verify_login(username: str, password: str) -> bool:
        """Login doğrula"""
        admin = AdminModel.get_collection().find_one({"username": username})
        
        if admin and admin.get("is_active"):
            password_hash = AdminModel.hash_password(password)
            return password_hash == admin["password"]
        
        return False
