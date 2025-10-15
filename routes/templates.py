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
import tempfile
import base64

templates_bp = Blueprint('templates', __name__)
logger = logging.getLogger(__name__)

# WhatsApp API Config
WHATSAPP_BUSINESS_ID = os.environ.get("WHATSAPP_BUSINESS_ID")
ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN") or os.environ.get("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

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

@templates_bp.route("/api/template-settings/save", methods=["POST"])
@login_required
def api_save_template_settings():
    """Template settings kaydet (alternative endpoint)"""
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

@templates_bp.route("/api/template-settings/<template_name>", methods=["GET"])
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

@templates_bp.route("/api/upload-whatsapp-image", methods=["POST"])
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
