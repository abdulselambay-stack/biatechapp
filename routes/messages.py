"""
Messages Routes
Direct messaging (text, image, etc.)
"""

from flask import Blueprint, request, jsonify
from routes.auth import login_required
from models import ChatModel
from utils import send_text_message, send_image_message
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
