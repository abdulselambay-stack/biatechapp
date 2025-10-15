"""
Products Routes
Product management
"""

from flask import Blueprint, request, jsonify, render_template
from routes.auth import login_required
from models import ProductModel
import logging

products_bp = Blueprint('products', __name__)
logger = logging.getLogger(__name__)

@products_bp.route("/products")
@login_required
def products_page():
    """Ürünler sayfası"""
    return render_template("products.html")

@products_bp.route("/api/products", methods=["GET"])
@login_required
def api_get_products():
    """Tüm ürünleri getir"""
    try:
        products = ProductModel.get_all_products()
        
        return jsonify({
            "success": True,
            "products": products
        })
    except Exception as e:
        logger.error(f"Get products error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@products_bp.route("/api/products/<product_id>", methods=["GET"])
@login_required
def api_get_product(product_id):
    """Tek bir ürünü getir"""
    try:
        product = ProductModel.get_product(product_id)
        
        if product:
            return jsonify({
                "success": True,
                "product": product
            })
        else:
            return jsonify({"success": False, "error": "Product not found"}), 404
    except Exception as e:
        logger.error(f"Get product error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@products_bp.route("/api/products", methods=["POST"])
@login_required
def api_create_product():
    """Yeni ürün ekle"""
    try:
        data = request.get_json()
        
        name = data.get("name")
        price = data.get("price")
        description = data.get("description", "")
        
        if not name or price is None:
            return jsonify({"success": False, "error": "name ve price gerekli"}), 400
        
        product_id = ProductModel.create_product(name, price, description)
        
        return jsonify({
            "success": True,
            "product_id": product_id,
            "message": "Ürün eklendi"
        })
    except Exception as e:
        logger.error(f"Create product error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@products_bp.route("/api/products/<product_id>", methods=["PUT"])
@login_required
def api_update_product(product_id):
    """Ürün güncelle"""
    try:
        data = request.get_json()
        
        success = ProductModel.update_product(product_id, data)
        
        return jsonify({
            "success": success,
            "message": "Ürün güncellendi" if success else "Ürün bulunamadı"
        })
    except Exception as e:
        logger.error(f"Update product error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@products_bp.route("/api/products/<product_id>", methods=["DELETE"])
@login_required
def api_delete_product(product_id):
    """Ürün sil"""
    try:
        success = ProductModel.delete_product(product_id)
        
        return jsonify({
            "success": success,
            "message": "Ürün silindi" if success else "Ürün bulunamadı"
        })
    except Exception as e:
        logger.error(f"Delete product error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
