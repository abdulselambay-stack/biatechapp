"""
Contacts Routes
Contact CRUD operations
"""

from flask import Blueprint, request, jsonify, render_template
from routes.auth import login_required
from models import ContactModel
import logging

contacts_bp = Blueprint('contacts', __name__)
logger = logging.getLogger(__name__)

@contacts_bp.route("/contacts")
@login_required
def contacts_page():
    """Kişiler sayfası"""
    return render_template("contacts.html")

@contacts_bp.route("/api/contacts-mongo", methods=["GET"])
@login_required
def api_get_contacts_mongo():
    """MongoDB'den tüm kişileri getir"""
    try:
        is_active = request.args.get('is_active')
        
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            contacts = ContactModel.get_all_contacts(is_active=is_active)
        else:
            contacts = ContactModel.get_all_contacts()
        
        return jsonify({
            "success": True,
            "contacts": contacts
        })
    except Exception as e:
        logger.error(f"Get contacts error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@contacts_bp.route("/api/contacts-mongo/<phone>", methods=["GET"])
@login_required
def api_get_contact_mongo(phone):
    """Tek bir kişiyi getir"""
    try:
        contact = ContactModel.get_contact(phone)
        
        if contact:
            return jsonify({
                "success": True,
                "contact": contact
            })
        else:
            return jsonify({"success": False, "error": "Contact not found"}), 404
    except Exception as e:
        logger.error(f"Get contact error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@contacts_bp.route("/api/contacts-mongo", methods=["POST"])
@login_required
def api_create_contact_mongo():
    """Yeni kişi ekle"""
    try:
        data = request.get_json()
        
        phone = data.get("phone")
        name = data.get("name")
        country = data.get("country", "")
        tags = data.get("tags", [])
        
        if not phone or not name:
            return jsonify({"success": False, "error": "phone ve name gerekli"}), 400
        
        # Kişi zaten var mı kontrol et
        existing = ContactModel.get_contact(phone)
        if existing:
            return jsonify({"success": False, "error": "Bu telefon numarası zaten kayıtlı"}), 400
        
        contact_id = ContactModel.create_contact(phone, name, country, tags)
        
        return jsonify({
            "success": True,
            "contact_id": contact_id,
            "message": "Kişi eklendi"
        })
    except Exception as e:
        logger.error(f"Create contact error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@contacts_bp.route("/api/contacts-mongo/<phone>", methods=["PUT"])
@login_required
def api_update_contact_mongo(phone):
    """Kişi güncelle"""
    try:
        data = request.get_json()
        
        success = ContactModel.update_contact(phone, data)
        
        return jsonify({
            "success": success,
            "message": "Kişi güncellendi" if success else "Kişi bulunamadı"
        })
    except Exception as e:
        logger.error(f"Update contact error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@contacts_bp.route("/api/contacts-mongo/<phone>", methods=["DELETE"])
@login_required
def api_delete_contact_mongo(phone):
    """Kişi sil"""
    try:
        success = ContactModel.delete_contact(phone)
        
        return jsonify({
            "success": success,
            "message": "Kişi silindi" if success else "Kişi bulunamadı"
        })
    except Exception as e:
        logger.error(f"Delete contact error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@contacts_bp.route("/api/contacts/sent-templates/<phone>", methods=["GET"])
@login_required  
def api_contact_sent_templates(phone):
    """Bir contact'a gönderilen template'leri getir"""
    try:
        contact = ContactModel.get_contact(phone)
        
        if not contact:
            return jsonify({"success": False, "error": "Contact not found"}), 404
        
        sent_templates = contact.get("sent_templates", [])
        
        return jsonify({
            "success": True,
            "phone": phone,
            "sent_templates": sent_templates
        })
    except Exception as e:
        logger.error(f"Get sent templates error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
