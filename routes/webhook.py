"""
Webhook Routes
WhatsApp Cloud API webhook handler
"""

from flask import Blueprint, request, jsonify
from models import WebhookLogModel, MessageModel, ChatModel, ContactModel
import logging
import datetime
import os

webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "biatech2024")

@webhook_bp.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "TechnoSender WhatsApp API",
        "timestamp": datetime.datetime.now().isoformat(),
        "verify_token": VERIFY_TOKEN
    })

@webhook_bp.route("/webhook/test")
def webhook_test():
    """Webhook test endpoint - Meta ayarlarını kontrol et"""
    return jsonify({
        "status": "ok",
        "message": "Webhook endpoint is working",
        "verify_token": VERIFY_TOKEN,
        "webhook_url": request.url_root + "webhook",
        "verify_url": request.url_root + "webhook?hub.mode=subscribe&hub.verify_token=" + VERIFY_TOKEN + "&hub.challenge=test123",
        "test": "Send a message to your WhatsApp number to test"
    })

def save_webhook_log(log_data):
    """Webhook'u JSON dosyasına kaydet (backward compatibility)"""
    import json
    log_file = "webhook_logs.json"
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        logs.append(log_data)
        
        # Son 1000 log'u tut
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        logger.error(f"Webhook log save error: {e}")

@webhook_bp.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta doğrulaması"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    logger.info("=" * 60)
    logger.info("🔍 WEBHOOK DOĞRULAMA İSTEĞİ")
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Token (gelen): {token}")
    logger.info(f"   Token (beklenen): {VERIFY_TOKEN}")
    logger.info(f"   Challenge: {challenge}")
    logger.info("=" * 60)

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ Webhook doğrulandı - Challenge döndürülüyor")
        return str(challenge), 200
    else:
        logger.error("❌ Doğrulama HATASI - Token eşleşmedi!")
        return "Verification failed", 403

@webhook_bp.route("/webhook", methods=["POST"])
def receive_webhook():
    """Gelen webhook'ları yakala ve MongoDB'ye kaydet"""
    data = request.get_json()
    
    try:
        value = data["entry"][0]["changes"][0]["value"]
        
        # Mesaj durumu (delivered, read, sent, failed)
        if "statuses" in value:
            status = value["statuses"][0]
            message_id = status["id"]
            status_type = status["status"]
            recipient = status.get("recipient_id", "unknown")
            
            logger.info(f"📦 Mesaj durumu: {status_type} → {message_id} (Alıcı: {recipient})")
            
            # MongoDB'ye webhook log kaydet
            WebhookLogModel.create_log(
                event_type="status",
                phone=recipient,
                data={"status": status_type, "message_id": message_id, "full_data": status}
            )
            
            # MessageModel'i güncelle
            if status_type in ["sent", "delivered", "read", "failed"]:
                error_msg = None
                if status_type == "failed" and "errors" in status:
                    error_msg = str(status["errors"])
                    logger.warning(f"   ⚠️  Failed message: {message_id} - {error_msg}")
                    
                    # NOT: sent_templates'den ÇIKARMIYORUZ
                    # Bir kez gönderildiyse, webhook failed gelse bile duplicate önlemek için
                    # MessageModel status'ü failed olarak işaretlenir ama tekrar gönderilmez
                
                MessageModel.update_status(
                    message_id=message_id,
                    status=status_type,
                    error=error_msg
                )
                logger.info(f"   ✅ Message status updated in MongoDB: {message_id} → {status_type}")
        
        # Gelen mesaj
        elif "messages" in value:
            msg = value["messages"][0]
            phone = msg["from"]
            message_type = msg["type"]
            message_id = msg["id"]
            
            # Mesaj içeriğini al
            content = ""
            media_url = None
            
            if message_type == "text":
                content = msg["text"]["body"]
            elif message_type == "image":
                content = msg.get("image", {}).get("caption", "(Resim)")
                media_url = msg.get("image", {}).get("link")
            elif message_type == "video":
                content = msg.get("video", {}).get("caption", "(Video)")
                media_url = msg.get("video", {}).get("link")
            elif message_type == "document":
                content = msg.get("document", {}).get("caption", "(Dosya)")
                media_url = msg.get("document", {}).get("link")
            else:
                content = f"({message_type})"
            
            logger.info(f"💬 Gelen mesaj: {phone} - {message_type}: {content[:50]}")
            
            # MongoDB'ye webhook log kaydet
            WebhookLogModel.create_log(
                event_type="incoming_message",
                phone=phone,
                data={"message_type": message_type, "content": content, "message_id": message_id}
            )
            
            # Chat history'e kaydet
            ChatModel.save_message(
                phone=phone,
                direction="incoming",
                message_type=message_type,
                content=content,
                media_url=media_url
            )
            logger.info(f"   ✅ Message saved to chat history: {phone}")
            
            # Contact yoksa otomatik ekle
            existing_contact = ContactModel.get_contact(phone)
            if not existing_contact:
                # Profile bilgilerini al (varsa)
                profile_name = value.get("contacts", [{}])[0].get("profile", {}).get("name", phone)
                
                ContactModel.create_contact(
                    phone=phone,
                    name=profile_name,
                    country="",
                    tags=["webhook"]  # Otomatik eklenen
                )
                logger.info(f"   ✅ New contact auto-added from webhook: {phone} ({profile_name})")
        
        # JSON dosyasına da yedek kaydet (backward compatibility)
        save_webhook_log({
            "timestamp": datetime.datetime.now().isoformat(),
            "data": data,
            "type": "status" if "statuses" in value else "incoming_message"
        })
        
    except Exception as e:
        logger.error(f"⚠️ Webhook parsing hatası: {e}")
        logger.error(f"   Data: {data}")
        
        # Hata durumunda da MongoDB'ye kaydet
        try:
            WebhookLogModel.create_log(
                event_type="error",
                phone=None,
                data={"error": str(e), "raw_data": data}
            )
        except:
            pass
    
    return "OK", 200
