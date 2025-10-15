"""
Sales Routes
Sales tracking and management
"""

from flask import Blueprint, request, jsonify, render_template
from routes.auth import login_required
from models import SalesModel, ContactModel, ProductModel
import logging

sales_bp = Blueprint('sales', __name__)
logger = logging.getLogger(__name__)

@sales_bp.route("/sales")
@login_required
def sales_page():
    """Satışlar sayfası"""
    return render_template("sales.html")

@sales_bp.route("/api/sales", methods=["GET"])
@login_required
def api_get_sales():
    """Tüm satışları getir"""
    try:
        sales = SalesModel.get_all_sales()
        
        # Contact ve product bilgilerini ekle
        for sale in sales:
            # Contact bilgisi
            contact = ContactModel.get_contact(sale['phone'])
            if contact:
                sale['contact_name'] = contact['name']
            else:
                sale['contact_name'] = sale['phone']
            
            # Product bilgisi
            product = ProductModel.get_product(sale['product_id'])
            if product:
                sale['product_name'] = product['name']
                sale['product_price'] = product['price']
            else:
                sale['product_name'] = "Unknown"
                sale['product_price'] = 0
        
        return jsonify({
            "success": True,
            "sales": sales
        })
    except Exception as e:
        logger.error(f"Get sales error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@sales_bp.route("/api/sales/<sale_id>", methods=["GET"])
@login_required
def api_get_sale(sale_id):
    """Tek bir satışı getir"""
    try:
        sale = SalesModel.get_sale(sale_id)
        
        if sale:
            return jsonify({
                "success": True,
                "sale": sale
            })
        else:
            return jsonify({"success": False, "error": "Sale not found"}), 404
    except Exception as e:
        logger.error(f"Get sale error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@sales_bp.route("/api/sales", methods=["POST"])
@login_required
def api_create_sale():
    """Yeni satış ekle"""
    try:
        data = request.get_json()
        
        phone = data.get("phone")
        product_id = data.get("product_id")
        quantity = data.get("quantity", 1)
        notes = data.get("notes", "")
        
        if not phone or not product_id:
            return jsonify({"success": False, "error": "phone ve product_id gerekli"}), 400
        
        sale_id = SalesModel.create_sale(phone, product_id, quantity, notes)
        
        return jsonify({
            "success": True,
            "sale_id": sale_id,
            "message": "Satış kaydedildi"
        })
    except Exception as e:
        logger.error(f"Create sale error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@sales_bp.route("/api/sales/<sale_id>", methods=["PUT"])
@login_required
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

@sales_bp.route("/api/sales/<sale_id>", methods=["DELETE"])
@login_required
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
