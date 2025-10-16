"""
Messages Routes
Direct messaging (text, image, etc.)
"""

from flask import Blueprint, request, jsonify
from routes.auth import login_required
from models import ChatModel
from utils import send_text_message, send_image_message, send_template_message
import logging

messages_bp = Blueprint('messages', __name__)
logger = logging.getLogger(__name__)

@messages_bp.route("/api/send-message", methods=["POST"])
@login_required
def api_send_message():
    """Text mesaj gönder"""
    try:
        data = request.get_json()
        
        phone = data.get("phone")
        message = data.get("message")
        
        if not phone or not message:
            return jsonify({"success": False, "error": "phone ve message gerekli"}), 400
        
        result = send_text_message(phone, message)
        
        if result["success"]:
            # Chat history'e kaydet
            ChatModel.save_message(
                phone=phone,
                direction="outgoing",
                message_type="text",
                content=message
            )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@messages_bp.route("/api/send-image", methods=["POST"])
@login_required
def api_send_image():
    """Görsel mesaj gönder"""
    try:
        data = request.get_json()
        
        phone = data.get("phone")
        image_url = data.get("image_url")
        caption = data.get("caption", "")
        
        if not phone or not image_url:
            return jsonify({"success": False, "error": "phone ve image_url gerekli"}), 400
        
        result = send_image_message(phone, image_url, caption)
        
        if result["success"]:
            # Chat history'e kaydet
            ChatModel.save_message(
                phone=phone,
                direction="outgoing",
                message_type="image",
                content=caption or "(Resim)",
                media_url=image_url
            )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Send image error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@messages_bp.route("/api/send-template", methods=["POST"])
@login_required
def api_send_template():
    """Template mesaj gönder (tek kişi veya toplu)"""
    try:
        data = request.get_json()
        
        phone_numbers = data.get("phone_numbers", [])
        template_name = data.get("template_name")
        language_code = data.get("language_code", "tr")
        
        if not phone_numbers or not template_name:
            return jsonify({"success": False, "error": "phone_numbers ve template_name gerekli"}), 400
        
        # Tek telefon numarası varsa
        if len(phone_numbers) == 1:
            phone = phone_numbers[0]
            result = send_template_message(phone, template_name, language_code=language_code)
            
            if result["success"]:
                # Chat history'e kaydet
                ChatModel.save_message(
                    phone=phone,
                    direction="outgoing",
                    message_type="template",
                    content=f"📤 Template: {template_name}"
                )
            
            return jsonify(result)
        else:
            # Toplu gönderim
            success_count = 0
            failed_count = 0
            
            for phone in phone_numbers:
                result = send_template_message(phone, template_name, language_code=language_code)
                
                if result["success"]:
                    success_count += 1
                    ChatModel.save_message(
                        phone=phone,
                        direction="outgoing",
                        message_type="template",
                        content=f"📤 Template: {template_name}"
                    )
                else:
                    failed_count += 1
            
            return jsonify({
                "success": True,
                "message": f"{success_count} başarılı, {failed_count} başarısız",
                "success_count": success_count,
                "failed_count": failed_count
            })
    except Exception as e:
        logger.error(f"Send template error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
