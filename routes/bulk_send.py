"""
Bulk Send Routes
Toplu mesaj gönderimi ve log'ları
"""

from flask import Blueprint, request, jsonify, render_template
from routes.auth import login_required
from models import ContactModel, MessageModel, ChatModel, TemplateSettingsModel
from utils import send_template_message
import logging

bulk_send_bp = Blueprint('bulk_send', __name__)
logger = logging.getLogger(__name__)

@bulk_send_bp.route("/bulk-send")
@login_required
def bulk_send_page():
    """Toplu gönderim sayfası"""
    return render_template("bulk_send.html")

@bulk_send_bp.route("/api/bulk-send/preview", methods=["GET"])
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

@bulk_send_bp.route("/api/bulk-send", methods=["POST"])
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

@bulk_send_bp.route("/api/bulk-send/logs", methods=["GET"])
@login_required
def api_bulk_send_logs():
    """Toplu gönderim log'larını getir"""
    try:
        template_name = request.args.get("template_name")
        limit = int(request.args.get("limit", 100))
        
        query = {}
        if template_name:
            query["template_name"] = template_name
        
        # TOPLAM kayıt sayısını al (limit yok)
        total_count = MessageModel.get_collection().count_documents(query)
        
        # Son gönderilen mesajları getir (limit ile)
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
            "total": total_count,  # Gerçek toplam
            "showing": len(logs)   # Gösterilen kayıt sayısı
        })
    except Exception as e:
        logger.error(f"Bulk send logs error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
