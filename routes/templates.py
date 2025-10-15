"""
Templates Routes
WhatsApp template management
"""

from flask import Blueprint, request, jsonify
from routes.auth import login_required
from models import TemplateSettingsModel
import os
import requests
import logging

templates_bp = Blueprint('templates', __name__)
logger = logging.getLogger(__name__)

# WhatsApp API Config
WHATSAPP_BUSINESS_ID = os.environ.get("WHATSAPP_BUSINESS_ID")
ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN") or os.environ.get("ACCESS_TOKEN")

@templates_bp.route("/api/templates", methods=["GET"])
@login_required
def api_get_templates():
    """Meta'dan template'leri çek"""
    try:
        url = f"https://graph.facebook.com/v21.0/{WHATSAPP_BUSINESS_ID}/message_templates"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            templates = data.get("data", [])
            
            # Sadece APPROVED template'leri filtrele
            approved_templates = [t for t in templates if t.get("status") == "APPROVED"]
            
            return jsonify({
                "success": True,
                "templates": approved_templates
            })
        else:
            logger.error(f"Template fetch error: {response.text}")
            return jsonify({
                "success": False,
                "error": f"API Error: {response.status_code}"
            }), response.status_code
            
    except Exception as e:
        logger.error(f"Template fetch error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@templates_bp.route("/api/templates/<template_name>/image-id", methods=["GET"])
@login_required
def api_get_template_image_id(template_name):
    """Template için kaydedilmiş image ID'yi getir"""
    try:
        image_id = TemplateSettingsModel.get_header_image_id(template_name)
        
        return jsonify({
            "success": True,
            "template_name": template_name,
            "header_image_id": image_id
        })
    except Exception as e:
        logger.error(f"Get template image ID error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@templates_bp.route("/api/templates/<template_name>/image-id", methods=["POST"])
@login_required
def api_save_template_image_id(template_name):
    """Template için image ID kaydet"""
    try:
        data = request.get_json()
        header_image_id = data.get("header_image_id", "")
        
        TemplateSettingsModel.save_header_image_id(template_name, header_image_id)
        
        return jsonify({
            "success": True,
            "message": "Image ID kaydedildi"
        })
    except Exception as e:
        logger.error(f"Save template image ID error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
