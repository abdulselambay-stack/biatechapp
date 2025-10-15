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
        
        return jsonify({
            "success": True,
            "sales": sales
        })
    except Exception as e:
        logger.error(f"Get sales error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@sales_bp.route("/api/sales/stats", methods=["GET"])
@login_required
def api_get_sales_stats():
    """Satış istatistiklerini getir"""
    try:
        stats = SalesModel.get_sales_stats()
        
        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Get sales stats error: {e}")
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
    """Yeni satış ekle (tier pricing destekli)"""
    try:
        data = request.get_json()
        
        phone = data.get("phone")
        customer_name = data.get("customer_name", "")
        product_id = data.get("product_id")
        quantity = data.get("quantity", 1)
        notes = data.get("notes", "")
        
        logger.info(f"Creating sale - phone: {phone}, product: {product_id}, quantity: {quantity} (type: {type(quantity)})")
        
        if not phone or not product_id:
            return jsonify({"success": False, "error": "Telefon ve ürün seçimi gerekli"}), 400
        
        # Customer name yoksa contact'tan çek
        if not customer_name:
            contact = ContactModel.get_contact(phone)
            customer_name = contact['name'] if contact else phone
        
        # Quantity'yi int'e çevir
        quantity = int(quantity) if quantity else 1
        
        sale = SalesModel.create_sale(
            phone=phone,
            customer_name=customer_name,
            product_id=product_id,
            quantity=quantity,
            notes=notes
        )
        
        return jsonify({
            "success": True,
            "sale": sale,
            "message": "Satış kaydedildi"
        })
    except ValueError as ve:
        logger.error(f"Value error in create sale: {ve}")
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Create sale error: {e}", exc_info=True)
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
