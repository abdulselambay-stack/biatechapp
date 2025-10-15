from flask import Flask, request, jsonify, send_from_directory, render_template, session, redirect, url_for
from functools import wraps
from dotenv import load_dotenv
import os
import json
import requests
import datetime
import threading
import time
import logging
from typing import List, Dict, Set

# MongoDB imports
from database import get_database
from models import ContactModel, MessageModel, SalesModel, ProductModel, TemplateSettingsModel, ChatModel, AdminModel, WebhookLogModel

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

load_env_file()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "technoglobal-secret-key-2025")

# ==================== LOGIN REQUIRED DECORATOR ====================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== AYARLAR ====================
VERIFY_TOKEN = "technoglobal123"
ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "YOUR_PHONE_NUMBER_ID_HERE")
WHATSAPP_API_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
WHATSAPP_BUSINESS_ID = os.environ.get("WHATSAPP_BUSINESS_ID", "1870559920510192")

# ==================== INITIALIZE DEFAULT ADMIN ====================
try:
    AdminModel.create_default_admin()
except Exception as e:
    logger.warning(f"⚠️  Admin oluşturulamadı: {e}")

# ==================== DOSYA YÖNETİMİ ====================
CONTACTS_FILE = os.path.join(os.path.dirname(__file__), "contacts_with_index.json")
MESSAGE_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "message_history.json")
WEBHOOK_LOG_FILE = os.path.join(os.path.dirname(__file__), "webhook_logs.json")
PROCESSED_FILE = os.path.join(os.path.dirname(__file__), "processed.json")
CSV_UPLOAD_FILE = "uploaded_contacts.json"

# ==================== GLOBAL KONTROL ====================
bulk_send_control = {
    "is_running": False,
    "should_stop": False,
    "current_progress": 0,
    "total_count": 0,
    "logs": []
}

def load_json(file_path, default=None):
    """JSON dosyasını yükle"""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else []

def save_json(file_path, data):
    """JSON dosyasına kaydet"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_message_history() -> Dict:
    """Mesaj geçmişini oku"""
    return load_json(MESSAGE_HISTORY_FILE)

def save_message_history(history: Dict):
    """Mesaj geçmişini kaydet"""
    save_json(MESSAGE_HISTORY_FILE, history)

def get_processed_contacts() -> Dict:
    """İşlenmiş kişileri oku (template bazlı)"""
    return load_json(PROCESSED_FILE, default={})

def save_processed_contacts(processed: Dict):
    """İşlenmiş kişileri kaydet"""
    save_json(PROCESSED_FILE, processed)

def add_to_processed(template_name: str, phone_numbers: List[str]):
    """Template için işlenmiş kişileri ekle"""
    processed = get_processed_contacts()
    if template_name not in processed:
        processed[template_name] = []
    
    # Yeni numaraları ekle (duplicate önleme)
    for phone in phone_numbers:
        if phone not in processed[template_name]:
            processed[template_name].append(phone)
    
    save_processed_contacts(processed)
    return len(processed[template_name])

def get_contacts() -> List[Dict]:
    """Kişi listesini yükle"""
    return load_json(CONTACTS_FILE, default=[])

def get_contact_name(phone_id: str) -> str:
    """Telefon numarasından kişi adını bul"""
    contacts = get_contacts()
    for contact in contacts:
        if contact["id"] == phone_id:
            return contact.get("name", contact.get("pushname", phone_id))
    return phone_id

def get_webhook_logs() -> List[Dict]:
    """Webhook loglarını yükle"""
    return load_json(WEBHOOK_LOG_FILE, default=[])

def save_webhook_log(log_entry: Dict):
    """Webhook logunu kaydet"""
    logs = get_webhook_logs()
    logs.append(log_entry)
    # Son 1000 logu tut
    if len(logs) > 1000:
        logs = logs[-1000:]
    save_json(WEBHOOK_LOG_FILE, logs)

def log_outgoing_message(phone_number: str, message_type: str, content: str, media_url: str = None, message_id: str = None):
    """Giden mesajı logla"""
    log_entry = {
        "type": "outgoing_message",
        "to": phone_number,
        "message_type": message_type,
        "content": content,
        "timestamp": datetime.datetime.now().isoformat()
    }
    if media_url:
        log_entry["media_url"] = media_url
    if message_id:
        log_entry["message_id"] = message_id
    save_webhook_log(log_entry)

# ==================== MESAJ GÖNDERİMİ ====================
def filter_recipients(template_name: str, all_contacts: List[Dict], limit: int) -> List[Dict]:
    """
    Daha önce bu şablonu almamış kişileri filtrele ve limite kadar seç (processed.json bazlı)
    """
    processed = get_processed_contacts()
    
    # Template için işlenmiş kişileri al
    if template_name not in processed:
        processed[template_name] = []
    
    processed_set = set(processed[template_name])
    
    # Daha önce gönderilmemiş kişileri filtrele
    eligible_contacts = [
        contact for contact in all_contacts 
        if contact["id"] not in processed_set
    ]
    
    # Limite kadar seç
    selected = eligible_contacts[:limit]
    
    return selected, len(eligible_contacts)

def send_template_message(phone_number: str, template_name: str, language_code: str = "tr", header_image_id: str = None) -> Dict:
    """
    WhatsApp Cloud API ile şablon mesajı gönder
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }
    }
    
    # Header image parametresi varsa ekle (boş string değilse)
    if header_image_id and header_image_id.strip():
        payload["template"]["components"] = [
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "image",
                        "image": {
                            "id": header_image_id.strip()
                        }
                    }
                ]
            }
        ]
        logger.info(f"Template with image header: {header_image_id}")
    
    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=10)
        
        # Log response for debugging
        logger.info(f"WhatsApp API Response: {response.status_code}")
        
        if response.status_code == 200:
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.json()
            }
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            logger.error(f"WhatsApp API Error: {error_msg}")
            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_msg,
                "response": error_data
            }
    except requests.Timeout:
        logger.error(f"Timeout while sending to {phone_number}")
        return {
            "success": False,
            "error": "Request timeout (10s)"
        }
    except Exception as e:
        logger.error(f"Exception while sending to {phone_number}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def send_text_message(phone_number: str, text: str) -> Dict:
    """
    WhatsApp Cloud API ile text mesajı gönder
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {
            "preview_url": True,
            "body": text
        }
    }
    
    try:
        logger.info(f"🚀 Sending text to {phone_number}")
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=10)
        response_data = response.json()
        
        if response.status_code == 200:
            logger.info(f"✅ Message sent successfully: {response_data}")
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response_data
            }
        else:
            logger.error(f"❌ WhatsApp API error {response.status_code}: {response_data}")
            return {
                "success": False,
                "status_code": response.status_code,
                "response": response_data,
                "error": response_data.get("error", {}).get("message", "Unknown error")
            }
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        return {
            "success": False,
            "error": f"Network error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return {
            "success": False,
            "error": f"Error: {str(e)}"
        }

def send_image_message(phone_number: str, image_url: str, caption: str = "") -> Dict:
    """
    WhatsApp Cloud API ile image mesajı gönder
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "image",
        "image": {
            "link": image_url
        }
    }
    
    if caption:
        payload["image"]["caption"] = caption
    
    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=10)
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response.json()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def upload_media(file_data: bytes, mime_type: str) -> Dict:
    """
    WhatsApp Cloud API'ye media upload et
    """
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/media"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    
    files = {
        'file': ('image.jpg', file_data, mime_type),
        'messaging_product': (None, 'whatsapp')
    }
    
    try:
        response = requests.post(url, headers=headers, files=files, timeout=30)
        if response.status_code == 200:
            return {
                "success": True,
                "media_id": response.json().get("id")
            }
        else:
            return {
                "success": False,
                "error": response.json()
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def send_image_with_media_id(phone_number: str, media_id: str, caption: str = "") -> Dict:
    """
    Media ID ile image mesajı gönder
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "image",
        "image": {
            "id": media_id
        }
    }
    
    if caption:
        payload["image"]["caption"] = caption
    
    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=10)
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response.json()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def update_message_history(template_name: str, phone_numbers: List[str]):
    """
    Mesaj geçmişini güncelle - başarıyla gönderilen numaraları kaydet
    """
    history = get_message_history()
    
    if template_name not in history:
        history[template_name] = []
    
    # Yeni numaraları ekle (duplicate kontrolü)
    existing = set(history[template_name])
    for phone in phone_numbers:
        if phone not in existing:
            history[template_name].append(phone)
    
    save_message_history(history)

# ==================== WEBHOOK ENDPOINTS ====================
@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "running",
        "service": "WhatsApp Cloud API",
        "webhook_url": "/webhook",
        "verify_token": "technoglobal123"
    })

@app.route("/webhook/test")
def webhook_test():
    """Webhook test endpoint - Meta ayarlarını kontrol et"""
    return jsonify({
        "webhook_url": "https://your-app.railway.app/webhook",
        "verify_token": VERIFY_TOKEN,
        "instructions": {
            "step_1": "Meta Business Manager > WhatsApp > Configuration",
            "step_2": "Webhook URL: https://your-app.railway.app/webhook",
            "step_3": f"Verify Token: {VERIFY_TOKEN}",
            "step_4": "Subscribe to: messages, message_status"
        },
        "test": "Send a message to your WhatsApp number to test"
    })

@app.route("/webhook", methods=["GET"])
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

@app.route("/webhook", methods=["POST"])
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

# ==================== AUTH ENDPOINTS ====================
@app.route("/login")
def login_page():
    """Login sayfası"""
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    """Login API"""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        if AdminModel.verify_login(username, password):
            session['logged_in'] = True
            session['username'] = username
            logger.info(f"✅ Login successful: {username}")
            return jsonify({"success": True})
        else:
            logger.warning(f"❌ Login failed: {username}")
            return jsonify({"success": False, "error": "Kullanıcı adı veya şifre hatalı"}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/logout", methods=["POST"])
def api_logout():
    """Logout API"""
    session.clear()
    return jsonify({"success": True})

# ==================== PAGE ROUTES (Protected) ====================
@app.route("/")
@login_required
def index():
    """Ana sayfa - Modern dashboard"""
    return render_template("dashboard_modern.html")

@app.route("/contacts")
@login_required
def contacts_page():
    """Kişiler sayfası"""
    return render_template("contacts.html")

@app.route("/campaigns")
@login_required
def campaigns_page():
    """Kampanyalar sayfası"""
    return render_template("campaigns.html")

@app.route("/analytics")
@login_required
def analytics_page():
    """Analitik sayfası"""
    return render_template("analytics.html")

@app.route("/settings")
@login_required
def settings():
    """Ayarlar sayfası"""
    return render_template("settings.html")

@app.route("/template-management")
@login_required
def template_management():
    """Şablon yönetimi sayfası"""
    return render_template("template_management.html")

@app.route("/chat")
@login_required
def chat_page():
    """Chat sayfası"""
    return render_template("chat.html")

@app.route("/sales")
@login_required
def sales_page():
    """Satışlar sayfası"""
    return render_template("sales.html")

@app.route("/products")
@login_required
def products_page():
    """Ürünler sayfası"""
    return render_template("products.html")

@app.route("/bulk-send")
@login_required
def bulk_send_page():
    """Toplu mesaj gönderimi sayfası"""
    return render_template("bulk_send.html")

@app.route("/uploads/<filename>")
def serve_upload(filename):
    """Upload edilmiş dosyaları serve et"""
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    return send_from_directory(uploads_dir, filename)

@app.route("/api/contacts", methods=["GET"])
def api_get_contacts():
    """Tüm kişileri getir"""
    contacts = get_contacts()
    return jsonify({
        "success": True,
        "total": len(contacts),
        "contacts": contacts
    })

@app.route("/api/history", methods=["GET"])
def api_get_history():
    """Mesaj geçmişini getir"""
    history = get_message_history()
    
    # İstatistikler ekle
    stats = {}
    for template, recipients in history.items():
        stats[template] = len(recipients)
    
    return jsonify({
        "success": True,
        "history": history,
        "stats": stats
    })

@app.route("/api/processed", methods=["GET"])
def api_get_processed():
    """İşlenmiş kişileri döndür (processed.json)"""
    processed = get_processed_contacts()
    
    # İstatistikler ekle
    stats = {}
    for template, recipients in processed.items():
        stats[template] = len(recipients)
    
    return jsonify({
        "success": True,
        "processed": processed,
        "stats": stats
    })

@app.route("/api/webhook-logs", methods=["GET"])
def api_get_webhook_logs():
    """Son webhook loglarını getir"""
    limit = int(request.args.get("limit", 50))
    logs = get_webhook_logs()
    return jsonify({
        "success": True,
        "total": len(logs),
        "logs": logs[-limit:]
    })

@app.route("/api/send", methods=["POST"])
def api_send_messages():
    """
    Mesaj gönder
    Body: {
        "template_name": "hello_world",
        "limit": 225,
        "language_code": "tr"
    }
    """
    data = request.get_json()
    
    template_name = data.get("template_name")
    limit = int(data.get("limit", 225))
    language_code = data.get("language_code", "tr")
    
    if not template_name:
        return jsonify({
            "success": False,
            "error": "template_name gerekli"
        }), 400
    
    # Kişileri yükle
    all_contacts = get_contacts()
    
    if not all_contacts:
        return jsonify({
            "success": False,
            "error": "Kişi listesi bulunamadı"
        }), 400
    
    # Daha önce gönderilmemiş kişileri filtrele
    selected_contacts, total_eligible = filter_recipients(template_name, all_contacts, limit)
    
    if not selected_contacts:
        return jsonify({
            "success": False,
            "error": f"Bu şablon zaten tüm kişilere gönderilmiş. Toplam uygun kişi: {total_eligible}",
            "total_eligible": total_eligible
        }), 400
    
    # Mesaj gönderme
    results = []
    successful_sends = []
    
    for contact in selected_contacts:
        phone = contact["id"]
        result = send_template_message(phone, template_name, language_code)
        
        results.append({
            "phone": phone,
            "name": contact.get("name", contact.get("pushname", "Unknown")),
            "success": result["success"],
            "result": result
        })
        
        if result["success"]:
            successful_sends.append(phone)
    
    # Başarılı gönderimler için geçmişi güncelle
    if successful_sends:
        update_message_history(template_name, successful_sends)
    
    return jsonify({
        "success": True,
        "template": template_name,
        "total_selected": len(selected_contacts),
        "total_eligible": total_eligible,
        "successful_sends": len(successful_sends),
        "failed_sends": len(selected_contacts) - len(successful_sends),
        "results": results
    })

@app.route("/api/upload-csv", methods=["POST"])
def api_upload_csv():
    """CSV dosyası yükle ve kişileri kaydet"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "Dosya bulunamadı"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Dosya seçilmedi"}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({"success": False, "error": "Sadece CSV dosyası yüklenebilir"}), 400
    
    try:
        # CSV'yi oku
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        contacts = []
        for row in csv_reader:
            # İlk sütun telefon numarası, ikinci sütun isim olmalı
            phone = row.get('phone') or row.get('telefon') or list(row.values())[0]
            name = row.get('name') or row.get('isim') or list(row.values())[1] if len(row) > 1 else phone
            
            contacts.append({
                "id": phone.strip(),
                "name": name.strip(),
                "pushname": name.strip()
            })
        
        # Mevcut kişilerle birleştir
        existing_contacts = get_contacts()
        existing_ids = {c["id"] for c in existing_contacts}
        
        new_contacts = [c for c in contacts if c["id"] not in existing_ids]
        all_contacts = existing_contacts + new_contacts
        
        # Kaydet
        save_json(CONTACTS_FILE, all_contacts)
        
        return jsonify({
            "success": True,
            "total_uploaded": len(contacts),
            "new_contacts": len(new_contacts),
            "total_contacts": len(all_contacts)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/preview-recipients", methods=["POST"])
def api_preview_recipients():
    """Seçilecek kişileri önizle"""
    data = request.get_json()
    template_name = data.get("template_name")
    limit = data.get("limit", 225)
    
    if not template_name:
        return jsonify({"success": False, "error": "template_name gerekli"}), 400
    
    all_contacts = get_contacts()
    selected_contacts, total_eligible = filter_recipients(template_name, all_contacts, limit)
    
    preview = [{
        "phone": c["id"],
        "name": c.get("name", c.get("pushname", c["id"]))
    } for c in selected_contacts]
    
    return jsonify({
        "success": True,
        "selected": preview,
        "selected_count": len(preview),
        "total_eligible": total_eligible,
        "total_contacts": len(all_contacts)
    })

@app.route("/api/send-bulk-stream", methods=["POST"])
def api_send_bulk_stream():
    """Toplu mesaj gönder - canlı log stream"""
    data = request.get_json()
    template_name = data.get("template_name")
    limit = data.get("limit", 225)
    language_code = data.get("language_code", "tr")  # Default: Türkçe
    header_image_id = data.get("header_image_id", "780517088218949")  # Default image ID
    messages_per_minute = data.get("messages_per_minute", 60)
    
    if bulk_send_control["is_running"]:
        return jsonify({"success": False, "error": "Bir gönderim zaten devam ediyor"}), 400
    
    # Thread'de çalıştır
    def send_bulk():
        bulk_send_control["is_running"] = True
        bulk_send_control["should_stop"] = False
        bulk_send_control["current_progress"] = 0
        bulk_send_control["logs"] = []
        
        # Rate limiting hesapla (saniye cinsinden)
        delay_seconds = 60.0 / messages_per_minute
        
        try:
            all_contacts = get_contacts()
            selected_contacts, total_eligible = filter_recipients(template_name, all_contacts, limit)
            bulk_send_control["total_count"] = len(selected_contacts)
            
            bulk_send_control["logs"].append(f"✅ {len(selected_contacts)} kişi seçildi")
            bulk_send_control["logs"].append(f"⏱️ Hız: {messages_per_minute} mesaj/dakika ({delay_seconds:.1f}s aralık)")
            
            history = get_message_history()
            if template_name not in history:
                history[template_name] = []
            
            successful_sends = []  # Başarılı gönderimler için
            
            for i, contact in enumerate(selected_contacts):
                if bulk_send_control["should_stop"]:
                    bulk_send_control["logs"].append("⏸️ Gönderim durduruldu")
                    break
                
                phone = contact["id"]
                name = contact.get("name", contact.get("pushname", phone))
                
                bulk_send_control["logs"].append(f"📤 {i+1}/{len(selected_contacts)}: {name} ({phone})")
                
                result = send_template_message(phone, template_name, language_code, header_image_id)
                
                if result["success"]:
                    bulk_send_control["logs"].append(f"✅ Başarılı: {name}")
                    history[template_name].append(phone)
                    save_message_history(history)
                    successful_sends.append(phone)  # Başarılı gönderimi kaydet
                else:
                    error_msg = result.get("response", {}).get("error", {}).get("message", "Bilinmeyen hata")
                    bulk_send_control["logs"].append(f"❌ Hata: {name} - {error_msg}")
                
                bulk_send_control["current_progress"] = i + 1
                time.sleep(delay_seconds)  # Rate limiting
            
            # Başarılı gönderimler processed.json'a ekle
            if successful_sends:
                total_processed = add_to_processed(template_name, successful_sends)
                bulk_send_control["logs"].append(f"📊 Toplam işlenen: {total_processed} kişi (Bu gönderim: {len(successful_sends)})")
            
            bulk_send_control["logs"].append("🎉 Gönderim tamamlandı!")
        except Exception as e:
            bulk_send_control["logs"].append(f"⚠️ HATA: {str(e)}")
        finally:
            bulk_send_control["is_running"] = False
    
    threading.Thread(target=send_bulk, daemon=True).start()
    
    return jsonify({"success": True, "message": "Gönderim başlatıldı"})

@app.route("/api/bulk-status")
def api_bulk_status():
    """Toplu gönderim durumunu getir"""
    return jsonify({
        "is_running": bulk_send_control["is_running"],
        "current_progress": bulk_send_control["current_progress"],
        "total_count": bulk_send_control["total_count"],
        "logs": bulk_send_control["logs"][-50:]  # Son 50 log
    })

@app.route("/api/bulk-stop", methods=["POST"])
def api_bulk_stop():
    """Toplu gönderimi durdur"""
    bulk_send_control["should_stop"] = True
    return jsonify({"success": True, "message": "Durdurma isteği gönderildi"})

@app.route("/api/upload-template-media", methods=["POST"])
def api_upload_template_media():
    """
    Template için media (resim) upload et
    Body: {
        "image_base64": "data:image/jpeg;base64,..."
    }
    """
    try:
        data = request.get_json()
        image_base64 = data.get("image_base64")
        
        if not image_base64:
            return jsonify({"success": False, "error": "image_base64 gerekli"}), 400
        
        # Base64'ü decode et
        if ',' in image_base64:
            header, encoded = image_base64.split(',', 1)
            mime_type = header.split(';')[0].split(':')[1]
        else:
            encoded = image_base64
            mime_type = "image/jpeg"
        
        file_data = base64.b64decode(encoded)
        
        # WhatsApp'a upload et
        upload_result = upload_media(file_data, mime_type)
        
        if upload_result["success"]:
            return jsonify({
                "success": True,
                "media_id": upload_result["media_id"],
                "message": "Resim yüklendi"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Upload hatası: {upload_result.get('error')}"
            }), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Sunucu hatası: {str(e)}"
        }), 500

@app.route("/api/send-text", methods=["POST"])
def api_send_text():
    """
    Text mesajı gönder
    Body: {
        "phone_number": "905551234567",
        "text": "Merhaba, nasılsınız?"
    }
    """
    try:
        data = request.get_json()
        print(f"📥 Text mesaj isteği: {data}")
        
        phone_number = data.get("phone_number")
        text = data.get("text")
        
        if not phone_number or not text:
            return jsonify({
                "success": False,
                "error": "phone_number ve text gerekli"
            }), 400
        
        print(f"📤 Text gönderiliyor: {phone_number}")
        
        result = send_text_message(phone_number, text)
        print(f"📊 Sonuç: {result}")
        
        if result["success"]:
            # Giden mesajı logla
            message_id = result.get("response", {}).get("messages", [{}])[0].get("id")
            log_outgoing_message(phone_number, "text", text, None, message_id)
            return jsonify({
                "success": True,
                "phone": phone_number,
                "message": "Mesaj gönderildi"
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Mesaj gönderilemedi"),
                "phone": phone_number
            }), 400
    except Exception as e:
        print(f"⚠️ Hata: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Sunucu hatası: {str(e)}"
        }), 500

@app.route("/api/send-image", methods=["POST"])
def api_send_image():
    """
    Image mesajı gönder (URL veya dosya upload)
    Body: {
        "phone_number": "905551234567",
        "image_url": "https://example.com/image.jpg",  // VEYA
        "image_base64": "data:image/jpeg;base64,...",
        "caption": "Opsiyonel açıklama"
    }
    """
    try:
        data = request.get_json()
        print(f"📥 Image mesaj isteği: {data.get('phone_number')}")
        
        phone_number = data.get("phone_number")
        image_url = data.get("image_url")
        image_base64 = data.get("image_base64")
        caption = data.get("caption", "")
        
        if not phone_number:
            return jsonify({"success": False, "error": "phone_number gerekli"}), 400
        
        if not image_url and not image_base64:
            return jsonify({"success": False, "error": "image_url veya image_base64 gerekli"}), 400
        
        # Base64 ile upload
        if image_base64:
            print(f"📤 Image upload ediliyor (base64): {phone_number}")
            
            # Base64'ü decode et
            if ',' in image_base64:
                header, encoded = image_base64.split(',', 1)
                mime_type = header.split(';')[0].split(':')[1]
                ext = mime_type.split('/')[1] if '/' in mime_type else 'jpg'
            else:
                encoded = image_base64
                mime_type = "image/jpeg"
                ext = "jpg"
            
            file_data = base64.b64decode(encoded)
            
            # Resmi local'e kaydet
            uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(uploads_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            # Local URL oluştur
            local_url = f"/uploads/{filename}"
            
            # WhatsApp'a upload et
            upload_result = upload_media(file_data, mime_type)
            
            if not upload_result["success"]:
                return jsonify({
                    "success": False,
                    "error": f"Upload hatası: {upload_result.get('error')}"
                }), 400
            
            media_id = upload_result["media_id"]
            print(f"✅ Media ID: {media_id}")
            
            # Media ID ile gönder
            result = send_image_with_media_id(phone_number, media_id, caption)
            
            # Local URL'i kaydet (önizleme için)
            media_url_to_log = local_url
        else:
            # URL ile gönder
            print(f"📤 Image gönderiliyor (URL): {phone_number}")
            result = send_image_message(phone_number, image_url, caption)
            media_url_to_log = image_url
        
        print(f"📊 Sonuç: {result}")
        
        if result["success"]:
            # Giden mesajı logla
            content = caption if caption else ""
            message_id = result.get("response", {}).get("messages", [{}])[0].get("id")
            log_outgoing_message(phone_number, "image", content, media_url_to_log, message_id)
            return jsonify({
                "success": True,
                "phone": phone_number,
                "message": "Resim gönderildi"
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Resim gönderilemedi"),
                "phone": phone_number
            }), 400
    except Exception as e:
        print(f"⚠️ Hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Sunucu hatası: {str(e)}"
        }), 500

@app.route("/api/send-combined", methods=["POST"])
def api_send_combined():
    """
    Text + Image birlikte gönder
    Body: {
        "phone_number": "905551234567",
        "text": "Bakın bu güzel!",
        "image_url": "https://...",  // VEYA
        "image_base64": "data:image/jpeg;base64,..."
    }
    """
    try:
        data = request.get_json()
        phone_number = data.get("phone_number")
        text = data.get("text", "")
        image_url = data.get("image_url")
        image_base64 = data.get("image_base64")
        
        if not phone_number:
            return jsonify({"success": False, "error": "phone_number gerekli"}), 400
        
        # Önce image gönder
        if image_base64:
            if ',' in image_base64:
                header, encoded = image_base64.split(',', 1)
                mime_type = header.split(';')[0].split(':')[1]
                ext = mime_type.split('/')[1] if '/' in mime_type else 'jpg'
            else:
                encoded = image_base64
                mime_type = "image/jpeg"
                ext = "jpg"
            
            file_data = base64.b64decode(encoded)
            
            # Resmi local'e kaydet
            uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(uploads_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            local_url = f"/uploads/{filename}"
            
            upload_result = upload_media(file_data, mime_type)
            
            if not upload_result["success"]:
                return jsonify({"success": False, "error": f"Upload hatası: {upload_result.get('error')}"}), 400
            
            result = send_image_with_media_id(phone_number, upload_result["media_id"], text)
            media_url_to_log = local_url
        elif image_url:
            result = send_image_message(phone_number, image_url, text)
            media_url_to_log = image_url
        else:
            return jsonify({"success": False, "error": "image_url veya image_base64 gerekli"}), 400
        
        if result["success"]:
            message_id = result.get("response", {}).get("messages", [{}])[0].get("id")
            log_outgoing_message(phone_number, "image", text, media_url_to_log, message_id)
            return jsonify({"success": True, "phone": phone_number, "message": "Text + Image gönderildi"})
        else:
            return jsonify({"success": False, "error": result.get("error")}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Sunucu hatası: {str(e)}"}), 500

@app.route("/api/send-single", methods=["POST"])
def api_send_single():
    """
    Tek bir kişiye mesaj gönder
    Body: {
        "phone_number": "905551234567",
        "template_name": "hello_world",
        "language_code": "tr",
        "header_image_id": "780517088218949"  # Opsiyonel
    }
    """
    try:
        data = request.get_json()
        print(f"📥 Template mesaj isteği: {data}")
        
        phone_number = data.get("phone_number")
        template_name = data.get("template_name")
        language_code = data.get("language_code", "tr")
        header_image_id = data.get("header_image_id", "780517088218949")  # Default image ID
        
        if not phone_number or not template_name:
            return jsonify({
                "success": False,
                "error": "phone_number ve template_name gerekli"
            }), 400
        
        print(f"📤 Template gönderiliyor: {phone_number} → {template_name}")
        
        result = send_template_message(phone_number, template_name, language_code, header_image_id)
        print(f"📊 Sonuç: {result}")
    except Exception as e:
        print(f"⚠️ Hata: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Sunucu hatası: {str(e)}"
        }), 500
    
    if result["success"]:
        # Giden mesajı logla
        message_id = result.get("response", {}).get("messages", [{}])[0].get("id")
        log_outgoing_message(phone_number, "template", f"[Template: {template_name}]", None, message_id)
        
        # processed.json'a ekle
        add_to_processed(template_name, [phone_number])
        
        return jsonify({
            "success": True,
            "phone": phone_number,
            "template": template_name,
            "message": "Mesaj başarıyla gönderildi"
        })
    else:
        return jsonify({
            "success": False,
            "error": result.get("error", "Mesaj gönderilemedi"),
            "phone": phone_number,
            "template": template_name
        }), 400

@app.route("/api/chat-history", methods=["GET"])
def api_chat_history():
    """
    Chat geçmişini getir - gelen ve giden mesajları grupla
    """
    logs = get_webhook_logs()
    contacts = get_contacts()
    
    # Kişi ID'sini isme çeviren dict
    contact_map = {c["id"]: c.get("name", c.get("pushname", c["id"])) for c in contacts}
    
    # Chat'leri grupla
    chats = {}
    
    for log in logs:
        # Gelen mesajlar
        if log.get("type") == "incoming_message":
            phone = log.get("from")
            if phone not in chats:
                chats[phone] = {
                    "phone": phone,
                    "name": contact_map.get(phone, phone),
                    "messages": [],
                    "last_message_time": log.get("timestamp")
                }
            msg_data = {
                "type": "incoming",
                "text": log.get("text", "(Medya)"),
                "timestamp": log.get("timestamp"),
                "message_type": log.get("message_type", "text")
            }
            if log.get("media_url"):
                msg_data["media_url"] = log.get("media_url")
            chats[phone]["messages"].append(msg_data)
            chats[phone]["last_message_time"] = log.get("timestamp")
        
        # Giden mesajlar
        elif log.get("type") == "outgoing_message":
            phone = log.get("to")
            if phone not in chats:
                chats[phone] = {
                    "phone": phone,
                    "name": contact_map.get(phone, phone),
                    "messages": [],
                    "last_message_time": log.get("timestamp")
                }
            msg_data = {
                "type": "outgoing",
                "text": log.get("content", "(Mesaj)"),
                "timestamp": log.get("timestamp"),
                "message_type": log.get("message_type", "text"),
                "message_id": log.get("message_id"),
                "status": "sent"  # Default status
            }
            if log.get("media_url"):
                msg_data["media_url"] = log.get("media_url")
            chats[phone]["messages"].append(msg_data)
            chats[phone]["last_message_time"] = log.get("timestamp")
    
    # Status'leri mesajlara eşleştir
    status_map = {}
    for log in logs:
        if log.get("type") == "status":
            msg_id = log.get("message_id")
            status = log.get("status")
            if msg_id:
                # En güncel status'u tut (read > delivered > sent)
                if msg_id not in status_map or (status == "read" or (status == "delivered" and status_map[msg_id] != "read")):
                    status_map[msg_id] = status
    
    # Status'leri mesajlara uygula
    for chat in chats.values():
        for msg in chat["messages"]:
            if msg.get("message_id") and msg["message_id"] in status_map:
                msg["status"] = status_map[msg["message_id"]]
        chat["messages"].sort(key=lambda x: x["timestamp"])
    
    # Liste olarak döndür, son mesaja göre sırala
    chat_list = sorted(chats.values(), key=lambda x: x["last_message_time"], reverse=True)
    
    return jsonify({
        "success": True,
        "chats": chat_list,
        "total": len(chat_list)
    })

@app.route("/api/check-duplicates", methods=["POST"])
def api_check_duplicates():
    """
    Bir şablonun daha önce gönderilip gönderilmediğini kontrol et
    Body: {
        "template_name": "hello_world",
        "phone_numbers": ["905551234567", "905559876543"]
    }
    """
    data = request.get_json()
    template_name = data.get("template_name")
    phone_numbers = data.get("phone_numbers", [])
    
    if not template_name or not phone_numbers:
        return jsonify({
            "success": False,
            "error": "template_name ve phone_numbers gerekli"
        }), 400
    
    history = get_message_history()
    sent_to = set(history.get(template_name, []))
    
    results = {}
    for phone in phone_numbers:
        results[phone] = {
            "already_sent": phone in sent_to
        }
    
    return jsonify({
        "success": True,
        "template": template_name,
        "results": results
    })

# İlk çalıştırmada gerekli dosyaları oluştur
if not os.path.exists(MESSAGE_HISTORY_FILE):
    save_json(MESSAGE_HISTORY_FILE, {})
if not os.path.exists(WEBHOOK_LOG_FILE):
    save_json(WEBHOOK_LOG_FILE, [])
if not os.path.exists(PROCESSED_FILE):
    save_json(PROCESSED_FILE, {})

# Startup logging (runs on import for both gunicorn and direct run)
logger.info("=" * 60)
logger.info("🚀 WhatsApp Cloud API Başlatılıyor...")
logger.info("=" * 60)

# Token kontrolü
if ACCESS_TOKEN == "YOUR_ACCESS_TOKEN_HERE" or not ACCESS_TOKEN:
    logger.warning("⚠️  UYARI: ACCESS_TOKEN ayarlanmamış!")
else:
    logger.info(f"✅ ACCESS_TOKEN yüklendi (ilk 10 karakter: {ACCESS_TOKEN[:10]}...)")

if PHONE_NUMBER_ID == "YOUR_PHONE_NUMBER_ID_HERE" or not PHONE_NUMBER_ID:
    logger.warning("⚠️  UYARI: PHONE_NUMBER_ID ayarlanmamış!")
else:
    logger.info(f"✅ PHONE_NUMBER_ID: {PHONE_NUMBER_ID}")

logger.info("=" * 60)
logger.info(f"📂 Kişi dosyası: {CONTACTS_FILE}")
logger.info(f"📂 Geçmiş dosyası: {MESSAGE_HISTORY_FILE}")
logger.info(f"📂 İşlenen dosyası: {PROCESSED_FILE}")
logger.info(f"📂 Webhook log dosyası: {WEBHOOK_LOG_FILE}")
logger.info("=" * 60)

# MongoDB bağlantısını başlat
try:
    db = get_database()
    logger.info(f"✅ MongoDB bağlantısı: {db.name}")
except Exception as e:
    logger.warning(f"⚠️ MongoDB bağlantısı başarısız (fallback to JSON): {e}")

# ==================== MONGODB API ENDPOINTS ====================

@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Dashboard istatistikleri - MongoDB"""
    try:
        stats = MessageModel.get_stats()
        contacts_count = ContactModel.get_collection().count_documents({"is_active": True})
        
        return jsonify({
            "total_contacts": contacts_count,
            "sent": stats.get("sent", 0),
            "delivered": stats.get("delivered", 0),
            "read": stats.get("read", 0),
            "failed": stats.get("failed", 0),
            "pending": stats.get("pending", 0),
            "total_messages": stats.get("total", 0)
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({
            "total_contacts": 0,
            "sent": 0,
            "delivered": 0,
            "read": 0,
            "failed": 0
        })

@app.route("/api/recent-activity", methods=["GET"])
def api_recent_activity():
    """Son aktiviteler"""
    try:
        logs = WebhookLogModel.get_recent_logs(limit=20)
        
        activities = []
        for log in logs:
            activity_type = log.get("event_type", "unknown")
            phone = log.get("phone", "Unknown")
            
            if activity_type == "status":
                status = log.get("data", {}).get("status", "unknown")
                activities.append({
                    "id": str(log["_id"]),
                    "type": status,
                    "message": f"Mesaj {status}: {phone}",
                    "time": log["timestamp"]
                })
            elif activity_type == "incoming_message":
                activities.append({
                    "id": str(log["_id"]),
                    "type": "incoming",
                    "message": f"Gelen mesaj: {phone}",
                    "time": log["timestamp"]
                })
        
        return jsonify(activities)
    except Exception as e:
        logger.error(f"Activity error: {e}")
        return jsonify([])

@app.route("/api/contacts-mongo", methods=["GET"])
def api_get_contacts_mongo():
    """MongoDB'den kişileri getir"""
    try:
        tags = request.args.get("tags")
        tag_list = tags.split(",") if tags else None
        
        contacts = ContactModel.get_all_contacts(tags=tag_list)
        
        return jsonify({
            "success": True,
            "contacts": contacts,
            "count": len(contacts)
        })
    except Exception as e:
        logger.error(f"Contacts error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/contacts-mongo", methods=["POST"])
def api_create_contact():
    """Yeni kişi ekle - MongoDB"""
    try:
        data = request.get_json()
        phone = data.get("phone")
        name = data.get("name")
        
        if not phone or not name:
            return jsonify({"success": False, "error": "Phone ve name gerekli"}), 400
        
        # Mevcut mi kontrol et
        existing = ContactModel.get_contact(phone)
        if existing:
            return jsonify({"success": False, "error": "Bu numara zaten kayıtlı"}), 400
        
        contact = ContactModel.create_contact(
            phone=phone,
            name=name,
            country=data.get("country", ""),
            tags=data.get("tags", [])
        )
        
        return jsonify({
            "success": True,
            "contact": contact
        })
    except Exception as e:
        logger.error(f"Create contact error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/contacts-mongo/<phone>", methods=["PUT"])
def api_update_contact(phone):
    """Kişi güncelle - MongoDB"""
    try:
        data = request.get_json()
        
        updates = {}
        if "name" in data:
            updates["name"] = data["name"]
        if "country" in data:
            updates["country"] = data["country"]
        if "tags" in data:
            updates["tags"] = data["tags"]
        
        success = ContactModel.update_contact(phone, updates)
        
        return jsonify({
            "success": success,
            "message": "Kişi güncellendi" if success else "Kişi bulunamadı"
        })
    except Exception as e:
        logger.error(f"Update contact error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/contacts-mongo/<phone>", methods=["DELETE"])
def api_delete_contact(phone):
    """Kişi sil - MongoDB"""
    try:
        success = ContactModel.delete_contact(phone)
        
        return jsonify({
            "success": success,
            "message": "Kişi silindi" if success else "Kişi bulunamadı"
        })
    except Exception as e:
        logger.error(f"Delete contact error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== CHAT API ENDPOINTS ====================

@app.route("/api/chats", methods=["GET"])
def api_get_chats():
    """
    Tüm chat'leri getir (MongoDB)
    
    Query params:
    - filter: all (default), incoming, unread, replied
    """
    try:
        filter_type = request.args.get('filter', 'all')
        chats = ChatModel.get_all_chats(filter_type=filter_type)
        
        # Her chat için contact bilgisini ekle
        for chat in chats:
            contact = ContactModel.get_contact(chat['phone'])
            if contact:
                chat['name'] = contact['name']
            else:
                chat['name'] = chat['phone']
        
        return jsonify({
            "success": True,
            "chats": chats,
            "filter": filter_type
        })
    except Exception as e:
        logger.error(f"Get chats error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/chat/<phone>", methods=["GET"])
def api_get_chat_history(phone):
    """Bir kişiyle olan chat geçmişini getir (MongoDB)"""
    try:
        limit = int(request.args.get("limit", 100))
        messages = ChatModel.get_chat_history(phone, limit=limit)
        
        # Mesajları okundu olarak işaretle
        ChatModel.mark_messages_as_read(phone)
        
        return jsonify({
            "success": True,
            "messages": messages
        })
    except Exception as e:
        logger.error(f"Get chat history error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/chat/mark-read/<phone>", methods=["POST"])
@login_required
def api_mark_chat_as_read(phone):
    """Bir chat'in mesajlarını okundu olarak işaretle"""
    try:
        ChatModel.mark_messages_as_read(phone)
        
        return jsonify({
            "success": True,
            "message": "Mesajlar okundu olarak işaretlendi"
        })
    except Exception as e:
        logger.error(f"Mark as read error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/chat/unread-count", methods=["GET"])
@login_required
def api_get_unread_count():
    """Toplam okunmamış mesaj sayısı"""
    try:
        unread_count = ChatModel.get_total_unread_count()
        
        return jsonify({
            "success": True,
            "unread_count": unread_count
        })
    except Exception as e:
        logger.error(f"Get unread count error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/chat/send", methods=["POST"])
def api_send_chat_message():
    """Chat'ten mesaj gönder (MongoDB'ye kaydet)"""
    try:
        data = request.get_json()
        phone = data.get("phone")
        message = data.get("message")
        
        if not phone or not message:
            return jsonify({"success": False, "error": "Phone ve message gerekli"}), 400
        
        logger.info(f"📤 Sending chat message to {phone}: {message[:50]}")
        
        # WhatsApp API'ye mesaj gönder
        result = send_text_message(phone, message)
        
        logger.info(f"📬 WhatsApp API response: {result}")
        
        if result.get("success"):
            # MongoDB'ye kaydet
            ChatModel.save_message(
                phone=phone,
                direction="outgoing",
                message_type="text",
                content=message
            )
            
            # MessageModel'e de kaydet
            message_id = result.get("response", {}).get("messages", [{}])[0].get("id")
            if message_id:
                MessageModel.create_message(
                    phone=phone,
                    template_name="manual_chat",
                    message_type="text",
                    content=message,
                    status="sent"
                )
                MessageModel.set_message_id(phone, "manual_chat", message_id)
            
            logger.info(f"✅ Chat message sent and saved: {phone}")
            
            return jsonify({
                "success": True,
                "message": "Mesaj gönderildi",
                "message_id": message_id
            })
        else:
            error_detail = result.get("error") or result.get("response", {})
            logger.error(f"❌ Message send failed: {error_detail}")
            
            return jsonify({
                "success": False,
                "error": f"WhatsApp API hatası: {error_detail}"
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Send chat message error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== PRODUCTS API ENDPOINTS ====================

@app.route("/api/products", methods=["GET"])
@login_required
def api_get_products():
    """Tüm ürünleri getir"""
    try:
        products = ProductModel.get_all_products()
        
        return jsonify({
            "success": True,
            "products": products,
            "count": len(products)
        })
    except Exception as e:
        logger.error(f"Get products error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/products", methods=["POST"])
@login_required
def api_create_product():
    """Yeni ürün oluştur"""
    try:
        data = request.get_json()
        
        name = data.get("name")
        cost_price = data.get("cost_price")
        sale_price = data.get("sale_price")
        description = data.get("description", "")
        category = data.get("category", "")
        currency = data.get("currency", "TRY")
        
        if not name or cost_price is None or sale_price is None:
            return jsonify({"success": False, "error": "Ürün adı, geliş ve satış fiyatı gerekli"}), 400
        
        product = ProductModel.create_product(
            name=name,
            cost_price=float(cost_price),
            sale_price=float(sale_price),
            description=description,
            category=category,
            currency=currency
        )
        
        logger.info(f"✅ Ürün oluşturuldu: {name} - Kar: {product['profit']} {product['currency']}")
        
        return jsonify({
            "success": True,
            "message": "Ürün oluşturuldu",
            "product": product
        })
    except Exception as e:
        logger.error(f"Create product error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/products/<product_id>", methods=["GET"])
@login_required
def api_get_product(product_id):
    """Ürün detayı getir"""
    try:
        product = ProductModel.get_product_by_id(product_id)
        
        if not product:
            return jsonify({"success": False, "error": "Ürün bulunamadı"}), 404
        
        return jsonify({
            "success": True,
            "product": product
        })
    except Exception as e:
        logger.error(f"Get product error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/products/<product_id>", methods=["PUT"])
@login_required
def api_update_product(product_id):
    """Ürün güncelle"""
    try:
        data = request.get_json()
        
        name = data.get("name")
        cost_price = data.get("cost_price")
        sale_price = data.get("sale_price")
        description = data.get("description", "")
        category = data.get("category", "")
        currency = data.get("currency", "TRY")
        
        if not name or cost_price is None or sale_price is None:
            return jsonify({"success": False, "error": "Ürün adı, geliş ve satış fiyatı gerekli"}), 400
        
        success = ProductModel.update_product(
            product_id=product_id,
            name=name,
            cost_price=float(cost_price),
            sale_price=float(sale_price),
            description=description,
            category=category,
            currency=currency
        )
        
        if success:
            logger.info(f"✅ Ürün güncellendi: {name}")
            return jsonify({
                "success": True,
                "message": "Ürün güncellendi"
            })
        else:
            return jsonify({"success": False, "error": "Ürün bulunamadı"}), 404
    except Exception as e:
        logger.error(f"Update product error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/products/<product_id>", methods=["DELETE"])
@login_required
def api_delete_product(product_id):
    """Ürün sil"""
    try:
        success = ProductModel.delete_product(product_id)
        
        if success:
            logger.info(f"✅ Ürün silindi: {product_id}")
            return jsonify({
                "success": True,
                "message": "Ürün silindi"
            })
        else:
            return jsonify({"success": False, "error": "Ürün bulunamadı"}), 404
    except Exception as e:
        logger.error(f"Delete product error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== SALES API ENDPOINTS ====================

@app.route("/api/sales", methods=["GET"])
def api_get_sales():
    """Tüm satışları getir"""
    try:
        limit = int(request.args.get("limit", 100))
        skip = int(request.args.get("skip", 0))
        
        sales = SalesModel.get_all_sales(limit=limit, skip=skip)
        
        return jsonify({
            "success": True,
            "sales": sales
        })
    except Exception as e:
        logger.error(f"Get sales error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sales/stats", methods=["GET"])
def api_get_sales_stats():
    """Satış istatistikleri"""
    try:
        stats = SalesModel.get_sales_stats()
        top_customers = SalesModel.get_top_customers(limit=5)
        
        return jsonify({
            "success": True,
            "stats": stats,
            "top_customers": top_customers
        })
    except Exception as e:
        logger.error(f"Get sales stats error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sales/<phone>", methods=["GET"])
def api_get_customer_sales(phone):
    """Bir müşterinin satışlarını getir"""
    try:
        sales = SalesModel.get_sales_by_phone(phone)
        
        return jsonify({
            "success": True,
            "sales": sales
        })
    except Exception as e:
        logger.error(f"Get customer sales error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sales", methods=["POST"])
def api_create_sale():
    """Yeni satış kaydı oluştur (ürün bazlı)"""
    try:
        data = request.get_json()
        
        phone = data.get("phone")
        customer_name = data.get("customer_name")
        product_id = data.get("product_id")
        quantity = data.get("quantity", 1)
        
        if not all([phone, customer_name, product_id]):
            return jsonify({
                "success": False,
                "error": "phone, customer_name, product_id gerekli"
            }), 400
        
        sale = SalesModel.create_sale(
            phone=phone,
            customer_name=customer_name,
            product_id=product_id,
            quantity=int(quantity),
            notes=data.get("notes", ""),
            currency=data.get("currency", "TRY")
        )
        
        logger.info(f"✅ Satış oluşturuldu: {customer_name} - {sale['product_name']} x{quantity} = {sale['total_amount']} TRY (Kar: {sale['total_profit']} TRY)")
        
        return jsonify({
            "success": True,
            "sale": sale
        })
    except Exception as e:
        logger.error(f"Create sale error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sales/<sale_id>", methods=["PUT"])
def api_update_sale(sale_id):
    """Satış güncelle"""
    try:
        data = request.get_json()
        success = SalesModel.update_sale(sale_id, data)
        
        return jsonify({
            "success": success,
            "message": "Satış güncellendi" if success else "Satış bulunamadı"
        })
    except Exception as e:
        logger.error(f"Update sale error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sales/<sale_id>", methods=["DELETE"])
def api_delete_sale(sale_id):
    """Satış sil"""
    try:
        success = SalesModel.delete_sale(sale_id)
        
        return jsonify({
            "success": success,
            "message": "Satış silindi" if success else "Satış bulunamadı"
        })
    except Exception as e:
        logger.error(f"Delete sale error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== ANALYTICS & DASHBOARD API ====================

@app.route("/api/analytics/stats", methods=["GET"])
@login_required
def api_analytics_stats():
    """Analytics sayfası için gerçek istatistikler"""
    try:
        from datetime import datetime, timedelta
        
        # Zaman aralığı
        time_range = request.args.get('range', '7d')
        now = datetime.utcnow()
        
        if time_range == '7d':
            start_date = now - timedelta(days=7)
        elif time_range == '30d':
            start_date = now - timedelta(days=30)
        elif time_range == '90d':
            start_date = now - timedelta(days=90)
        else:  # all
            start_date = datetime(2020, 1, 1)
        
        # Mesaj istatistikleri (sent_at kullan) - SADECE BAŞARILI MESAJLAR
        messages_pipeline = [
            {"$match": {
                "sent_at": {"$gte": start_date},
                "status": {"$in": ["sent", "delivered", "read"]}  # Failed HARİÇ
            }},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        message_stats = list(MessageModel.get_collection().aggregate(messages_pipeline))
        stats_dict = {item['_id']: item['count'] for item in message_stats}
        
        # Sadece gerçek gönderilen mesajları say
        sent_messages = stats_dict.get('sent', 0)
        delivered_messages = stats_dict.get('delivered', 0)
        read_messages = stats_dict.get('read', 0)
        
        total_messages = sent_messages + delivered_messages + read_messages
        
        # Failed mesajları ayrı say (gösterim için)
        failed_messages = MessageModel.get_collection().count_documents({
            "sent_at": {"$gte": start_date},
            "status": "failed"
        })
        
        # Toplam kişi sayısı
        total_contacts = ContactModel.get_collection().count_documents({})
        
        # Başarı oranları (delivered + read)
        successful_total = delivered_messages + read_messages
        success_rate = round((successful_total / total_messages * 100), 1) if total_messages > 0 else 0
        read_rate = round((read_messages / total_messages * 100), 1) if total_messages > 0 else 0
        
        return jsonify({
            "success": True,
            "stats": {
                "total_messages": total_messages,
                "sent_messages": sent_messages,
                "delivered_messages": delivered_messages,
                "read_messages": read_messages,
                "failed_messages": failed_messages,
                "success_rate": success_rate,
                "read_rate": read_rate,
                "total_contacts": total_contacts
            }
        })
    except Exception as e:
        logger.error(f"Analytics stats error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/analytics/daily", methods=["GET"])
@login_required
def api_analytics_daily():
    """Günlük mesaj istatistikleri"""
    try:
        from datetime import datetime, timedelta
        
        # Son 30 günü getir
        days = int(request.args.get('days', 30))
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        # Günlere göre groupla
        pipeline = [
            {"$match": {
                "sent_at": {"$gte": start_date},
                "status": {"$in": ["sent", "delivered", "read"]}
            }},
            {"$group": {
                "_id": {
                    "year": {"$year": "$sent_at"},
                    "month": {"$month": "$sent_at"},
                    "day": {"$dayOfMonth": "$sent_at"}
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        daily_stats = list(MessageModel.get_collection().aggregate(pipeline))
        
        # Format data
        formatted_data = []
        for stat in daily_stats:
            date_obj = datetime(
                year=stat['_id']['year'],
                month=stat['_id']['month'],
                day=stat['_id']['day']
            )
            formatted_data.append({
                "date": date_obj.strftime("%Y-%m-%d"),
                "count": stat['count']
            })
        
        return jsonify({
            "success": True,
            "data": formatted_data
        })
    except Exception as e:
        logger.error(f"Daily analytics error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/dashboard/stats", methods=["GET"])
@login_required
def api_dashboard_stats():
    """Dashboard için gerçek istatistikler"""
    try:
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        week_start = now - timedelta(days=7)
        
        # Toplam gönderilen mesajlar (sadece sent, delivered, read)
        total_messages = MessageModel.get_collection().count_documents({
            "status": {"$in": ["sent", "delivered", "read"]}
        })
        
        # Bugün gönderilen mesajlar (sent_at kullan)
        today_messages = MessageModel.get_collection().count_documents({
            "sent_at": {"$gte": today_start},
            "status": {"$in": ["sent", "delivered", "read"]}
        })
        
        # Toplam kişiler
        total_contacts = ContactModel.get_collection().count_documents({})
        
        # Aktif kampanyalar
        active_campaigns = CampaignModel.get_collection().count_documents({
            "status": {"$in": ["running", "pending"]}
        })
        
        # Bu hafta gönderilen mesajlar (sent_at kullan)
        week_messages = MessageModel.get_collection().count_documents({
            "sent_at": {"$gte": week_start},
            "status": {"$in": ["sent", "delivered", "read"]}
        })
        
        # Başarılı mesajlar (delivered ve read)
        successful_messages = MessageModel.get_collection().count_documents({
            "status": {"$in": ["delivered", "read"]}
        })
        
        # Başarı oranı (delivered+read / total)
        success_rate = round((successful_messages / total_messages * 100), 1) if total_messages > 0 else 0
        
        # Okunmamış mesajlar
        unread_messages = ChatModel.get_total_unread_count()
        
        # Son kampanyalar
        recent_campaigns = list(CampaignModel.get_collection()
                               .find()
                               .sort("created_at", -1)
                               .limit(5))
        
        for campaign in recent_campaigns:
            campaign['_id'] = str(campaign['_id'])
            if campaign.get('created_at'):
                campaign['created_at'] = campaign['created_at'].isoformat()
        
        return jsonify({
            "success": True,
            "stats": {
                "total_messages": total_messages,
                "today_messages": today_messages,
                "week_messages": week_messages,
                "total_contacts": total_contacts,
                "active_campaigns": active_campaigns,
                "success_rate": success_rate,
                "unread_messages": unread_messages,
                "recent_campaigns": recent_campaigns
            }
        })
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== TEMPLATE API ====================

@app.route("/api/templates", methods=["GET"])
@login_required
def api_get_templates():
    """Meta API'den template'leri çek"""
    try:
        url = f"https://graph.facebook.com/v24.0/{WHATSAPP_BUSINESS_ID}/message_templates"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }
        
        logger.info(f"📋 Fetching templates from Meta API...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            templates = data.get("data", [])
            
            # Template'leri formatla
            formatted_templates = []
            for template in templates:
                formatted_templates.append({
                    "id": template.get("id"),
                    "name": template.get("name"),
                    "language": template.get("language"),
                    "status": template.get("status"),
                    "category": template.get("category"),
                    "components": template.get("components", [])
                })
            
            logger.info(f"✅ {len(formatted_templates)} template loaded from Meta")
            
            return jsonify({
                "success": True,
                "templates": formatted_templates,
                "count": len(formatted_templates)
            })
        else:
            error_data = response.json()
            logger.error(f"❌ Meta API error: {error_data}")
            return jsonify({
                "success": False,
                "error": error_data.get("error", {}).get("message", "Template'ler alınamadı")
            }), response.status_code
            
    except Exception as e:
        logger.error(f"Template fetch error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== BULK SEND API ENDPOINTS ====================

@app.route("/api/bulk-send/preview", methods=["GET"])
@login_required
def api_bulk_send_preview():
    """
    Toplu gönderim öncesi istatistik
    
    Kontroller:
    1. sent_templates field (ContactModel)
    2. MessageModel'deki başarılı gönderimler (sent/delivered/read)
    """
    try:
        template_name = request.args.get("template_name")
        limit_str = request.args.get("limit", "")
        
        if not template_name:
            return jsonify({"success": False, "error": "template_name gerekli"}), 400
        
        # Tüm aktif kişileri getir
        all_contacts = ContactModel.get_all_contacts(is_active=True)
        
        # MessageModel'de bu template için başarılı gönderim yapılmış telefonları al
        messages_sent = MessageModel.get_collection().distinct("phone", {
            "template_name": template_name,
            "status": {"$in": ["sent", "delivered", "read"]}
        })
        messages_sent_set = set(messages_sent)
        
        # Daha önce almamış olanları filtrele (hem sent_templates hem MessageModel kontrolü)
        eligible_contacts = []
        already_sent_count = 0
        
        for contact in all_contacts:
            phone = contact["phone"]
            
            # sent_templates veya MessageModel'de varsa skip
            if template_name in contact.get("sent_templates", []) or phone in messages_sent_set:
                already_sent_count += 1
            else:
                eligible_contacts.append(contact)
        
        # Limit varsa uygula
        will_send = len(eligible_contacts)
        if limit_str and limit_str.isdigit():
            limit = int(limit_str)
            will_send = min(limit, len(eligible_contacts))
        
        stats = {
            "total_recipients": len(all_contacts),
            "already_sent": already_sent_count,
            "will_send": will_send
        }
        
        logger.info(f"📊 Preview: {len(all_contacts)} total, {already_sent_count} already sent ({len(messages_sent_set)} in messages), {len(eligible_contacts)} eligible")
        
        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Bulk send preview error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/bulk-send", methods=["POST"])
@login_required
def api_bulk_send():
    """Toplu mesaj gönderimi (duplicate kontrolü ile + detaylı log)"""
    try:
        data = request.get_json()
        
        template_name = data.get("template_name")
        limit = data.get("limit")
        header_image_id = data.get("header_image_id", "")  # Opsiyonel image ID
        
        if not template_name:
            return jsonify({"success": False, "error": "template_name gerekli"}), 400
        
        # Eğer image ID girilmemişse, kaydedilmiş default ID'yi yükle
        if not header_image_id:
            saved_image_id = TemplateSettingsModel.get_header_image_id(template_name)
            if saved_image_id:
                header_image_id = saved_image_id
                logger.info(f"📷 Using saved image ID for {template_name}: {header_image_id}")
        
        # Alıcıları belirle (daha önce almamış olanlar)
        recipients = ContactModel.get_contacts_without_template(template_name)
        
        if not recipients:
            return jsonify({
                "success": False,
                "error": "Gönderilecek kişi bulunamadı (tümü daha önce almış)"
            }), 400
        
        # Limit varsa uygula (type conversion)
        if limit:
            try:
                limit_int = int(limit)
                if limit_int > 0:
                    recipients = recipients[:limit_int]
                    logger.info(f"⚠️ LIMIT APPLIED: {limit_int} recipients (original: {len(recipients)})")
            except (ValueError, TypeError):
                pass
        
        logger.info(f"🚀 Bulk send starting: {template_name} to {len(recipients)} recipients")
        
        # Gönderim yap
        success_count = 0
        failed_count = 0
        skipped_count = 0
        details = []
        
        # Progress logging
        total_recipients = len(recipients)
        
        for i, contact in enumerate(recipients, 1):
            phone = contact["phone"]
            name = contact.get("name", "Unknown")
            
            # Triple check - sent_templates ve MessageModel'de kontrol
            if ContactModel.has_received_template(phone, template_name):
                skipped_count += 1
                details.append({
                    "phone": phone,
                    "name": name,
                    "status": "skipped",
                    "error": "Already sent (in sent_templates)"
                })
                logger.warning(f"⏭️  Skipped (in sent_templates): {name} ({phone})")
                continue
            
            # MessageModel'de başarılı gönderim var mı kontrol et
            existing_message = MessageModel.get_collection().find_one({
                "phone": phone,
                "template_name": template_name,
                "status": {"$in": ["sent", "delivered", "read"]}
            })
            
            if existing_message:
                skipped_count += 1
                details.append({
                    "phone": phone,
                    "name": name,
                    "status": "skipped",
                    "error": "Already sent (in messages)"
                })
                logger.warning(f"⏭️  Skipped (already in messages): {name} ({phone})")
                
                # Eğer sent_templates'de yoksa ekle (senkronize et)
                if not ContactModel.has_received_template(phone, template_name):
                    ContactModel.add_sent_template(phone, template_name)
                    logger.info(f"   ✅ Synced to sent_templates")
                continue
            
            # Progress log (her 10 mesajda bir)
            if i % 10 == 0 or i == total_recipients:
                logger.info(f"📊 Progress: {i}/{total_recipients} ({(i/total_recipients*100):.1f}%) - ✅ {success_count} ❌ {failed_count} ⏭️ {skipped_count}")
            
            # Mesaj gönder (image_id ile)
            result = send_template_message(phone, template_name, language_code="tr", header_image_id=header_image_id)
            
            if result["success"]:
                # ✅ BAŞARILI - template geçmişine ekle
                ContactModel.add_sent_template(phone, template_name)
                MessageModel.create_message(
                    phone=phone,
                    template_name=template_name,
                    status="sent"
                )
                
                # Chat'e kaydet (Toplu Gönderim)
                ChatModel.save_message(
                    phone=phone,
                    direction="outgoing",
                    message_type="template",
                    content=f"📤 Toplu Gönderim: {template_name}",
                    media_url=None
                )
                
                success_count += 1
                details.append({
                    "phone": phone,
                    "name": name,
                    "status": "success"
                })
                logger.info(f"✅ [{i}/{total_recipients}] Sent to {name} ({phone})")
            else:
                # ❌ BAŞARISIZ - template geçmişine EKLEME (önemli!)
                MessageModel.create_message(
                    phone=phone,
                    template_name=template_name,
                    status="failed",
                    error_message=result.get("error", "Unknown error")
                )
                failed_count += 1
                details.append({
                    "phone": phone,
                    "name": name,
                    "status": "failed",
                    "error": result.get("error", "Unknown error")
                })
                logger.error(f"❌ [{i}/{total_recipients}] Failed to {name} ({phone}): {result.get('error')}")
        
        logger.info(f"✅ Bulk send completed: {success_count} success, {failed_count} failed, {skipped_count} skipped")
        
        return jsonify({
            "success": True,
            "template": template_name,
            "results": {
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "total": len(recipients)
            },
            "details": details  # Detaylı log
        })
    except Exception as e:
        logger.error(f"Bulk send error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== BULK SEND LOGS API ====================

@app.route("/api/bulk-send/logs", methods=["GET"])
@login_required
def api_bulk_send_logs():
    """Toplu gönderim log'larını getir"""
    try:
        template_name = request.args.get("template_name")
        limit = int(request.args.get("limit", 100))
        
        query = {}
        if template_name:
            query["template_name"] = template_name
        
        # Son gönderilen mesajları getir
        messages = list(MessageModel.get_collection()
                       .find(query)
                       .sort("sent_at", -1)
                       .limit(limit))
        
        # Contact bilgilerini ekle
        logs = []
        for msg in messages:
            phone = msg.get("phone")
            contact = ContactModel.get_contact(phone)
            
            logs.append({
                "phone": phone,
                "name": contact.get("name", "Unknown") if contact else "Unknown",
                "template_name": msg.get("template_name"),
                "status": msg.get("status"),
                "sent_at": msg.get("sent_at").isoformat() if msg.get("sent_at") else None,
                "error_message": msg.get("error_message")
            })
        
        return jsonify({
            "success": True,
            "logs": logs,
            "total": len(logs)
        })
    except Exception as e:
        logger.error(f"Bulk send logs error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/contacts/sent-templates/<phone>", methods=["GET"])
@login_required  
def api_contact_sent_templates(phone):
    """Bir contact'a gönderilen template'leri getir"""
    try:
        contact = ContactModel.get_contact(phone)
        
        if not contact:
            return jsonify({"success": False, "error": "Contact bulunamadı"}), 404
        
        sent_templates = contact.get("sent_templates", [])
        
        return jsonify({
            "success": True,
            "phone": phone,
            "name": contact.get("name"),
            "sent_templates": sent_templates
        })
    except Exception as e:
        logger.error(f"Get sent templates error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== IMAGE UPLOAD API ====================

@app.route("/api/upload-whatsapp-image", methods=["POST"])
@login_required
def api_upload_whatsapp_image():
    """WhatsApp'a image yükle ve ID'sini kaydet"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "Dosya bulunamadı"}), 400
        
        file = request.files['file']
        template_name = request.form.get('template_name')
        
        if file.filename == '':
            return jsonify({"success": False, "error": "Dosya seçilmedi"}), 400
        
        if not template_name:
            return jsonify({"success": False, "error": "template_name gerekli"}), 400
        
        # Dosyayı geçici olarak kaydet
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
        file.save(temp_file.name)
        temp_file.close()
        
        try:
            # WhatsApp Media Upload API
            url = f"https://graph.facebook.com/v24.0/{PHONE_NUMBER_ID}/media"
            
            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }
            
            # Dosya tipini belirle
            content_type = file.content_type or 'image/jpeg'
            
            with open(temp_file.name, 'rb') as f:
                files = {
                    'file': (file.filename, f, content_type)
                }
                data = {
                    'messaging_product': 'whatsapp'
                }
                
                logger.info(f"📤 Uploading image to WhatsApp: {file.filename}")
                response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                media_id = result.get('id')
                
                # Template için image ID'yi kaydet
                TemplateSettingsModel.set_header_image_id(template_name, media_id)
                
                logger.info(f"✅ Image uploaded successfully: {media_id}")
                
                return jsonify({
                    "success": True,
                    "media_id": media_id,
                    "template_name": template_name,
                    "message": "Image yüklendi ve template'e atandı"
                })
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"❌ WhatsApp upload error: {error_msg}")
                
                return jsonify({
                    "success": False,
                    "error": error_msg,
                    "details": error_data
                }), response.status_code
        
        finally:
            # Geçici dosyayı sil
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    except Exception as e:
        logger.error(f"Image upload error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/template-settings/save", methods=["POST"])
@login_required
def api_save_template_settings():
    """Template settings kaydet"""
    try:
        data = request.get_json()
        template_name = data.get("template_name")
        image_id = data.get("image_id")
        
        if not template_name or not image_id:
            return jsonify({"success": False, "error": "template_name ve image_id gerekli"}), 400
        
        success = TemplateSettingsModel.set_header_image_id(template_name, image_id)
        
        if success:
            return jsonify({"success": True, "message": "Image ID kaydedildi"})
        else:
            return jsonify({"success": False, "error": "Kaydetme başarısız"}), 500
    except Exception as e:
        logger.error(f"Save template settings error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/template-settings/<template_name>", methods=["GET"])
@login_required
def api_get_template_settings(template_name):
    """Template ayarlarını getir"""
    try:
        settings = TemplateSettingsModel.get_template_settings(template_name)
        
        if settings:
            return jsonify({
                "success": True,
                "settings": settings
            })
        else:
            return jsonify({
                "success": True,
                "settings": {
                    "template_name": template_name,
                    "header_image_id": None
                }
            })
    except Exception as e:
        logger.error(f"Get template settings error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Only run Flask dev server when executed directly (not with gunicorn)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5005))
    logger.info("🌐 Flask Development Server")
    logger.info(f"📍 Port: {port}")
    logger.info("⚠️  Use gunicorn for production!")
    logger.info("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
