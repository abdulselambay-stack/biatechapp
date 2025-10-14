from flask import Flask, request, jsonify, send_from_directory, render_template
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
from models import ContactModel, MessageModel, CampaignModel, WebhookLogModel, ChatModel

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
    
    # Header image parametresi varsa ekle
    if header_image_id:
        payload["template"]["components"] = [
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "image",
                        "image": {
                            "id": header_image_id
                        }
                    }
                ]
            }
        ]
    
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
    """Gelen webhook'ları yakala ve kaydet"""
    data = request.get_json()
    timestamp = datetime.datetime.now().isoformat()
    
    log_entry = {
        "timestamp": timestamp,
        "data": data
    }
    
    try:
        value = data["entry"][0]["changes"][0]["value"]
        
        # Mesaj durumu (delivered, read, sent, failed)
        if "statuses" in value:
            status = value["statuses"][0]
            log_entry["type"] = "status"
            log_entry["status"] = status["status"]
            log_entry["message_id"] = status["id"]
            log_entry["recipient"] = status.get("recipient_id", "unknown")
            
            logger.info(f"📦 Mesaj durumu: {status['status']} → {status['id']}")
        
        # Gelen mesaj
        elif "messages" in value:
            msg = value["messages"][0]
            log_entry["type"] = "incoming_message"
            log_entry["from"] = msg["from"]
            log_entry["message_type"] = msg["type"]
            
            if msg["type"] == "text":
                log_entry["text"] = msg["text"]["body"]
            elif msg["type"] == "image":
                log_entry["text"] = msg.get("image", {}).get("caption", "(Resim)")
                log_entry["media_url"] = msg.get("image", {}).get("link")
            elif msg["type"] == "video":
                log_entry["text"] = msg.get("video", {}).get("caption", "(Video)")
                log_entry["media_url"] = msg.get("video", {}).get("link")
            elif msg["type"] == "document":
                log_entry["text"] = msg.get("document", {}).get("caption", "(Dosya)")
                log_entry["media_url"] = msg.get("document", {}).get("link")
            else:
                log_entry["text"] = f"({msg['type']})"
            
            logger.info(f"💬 Gelen mesaj: {msg['from']} - {msg['type']}")
        
        save_webhook_log(log_entry)
        
    except Exception as e:
        logger.error(f"⚠️ Webhook parsing hatası: {e}")
        log_entry["error"] = str(e)
        save_webhook_log(log_entry)
    
    return "OK", 200

# ==================== API ENDPOINTS ====================
@app.route("/")
def index():
    """Ana sayfa - Modern dashboard"""
    return render_template("dashboard_modern.html")

@app.route("/contacts")
def contacts_page():
    """Kişiler sayfası"""
    return render_template("contacts.html")

@app.route("/campaigns")
def campaigns_page():
    """Kampanyalar sayfası"""
    return render_template("campaigns.html")

@app.route("/analytics")
def analytics_page():
    """Analitik sayfası"""
    return render_template("analytics.html")

@app.route("/settings")
def settings_page():
    """Ayarlar sayfası"""
    return render_template("settings.html")

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

# Only run Flask dev server when executed directly (not with gunicorn)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5005))
    logger.info("🌐 Flask Development Server")
    logger.info(f"📍 Port: {port}")
    logger.info("⚠️  Use gunicorn for production!")
    logger.info("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
