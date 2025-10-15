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
        product = ProductModel.get_product_by_id(product_id)
        
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
    
@products_bp.route("/api/products/<product_id>/calculate", methods=["POST"])
@login_required
def api_calculate_price(product_id):
    """Miktara göre fiyat hesapla (tier pricing)"""
    try:
        data = request.get_json()
        quantity = data.get("quantity", 1)
        
        product = ProductModel.get_product_by_id(product_id)
        if not product:
            return jsonify({"success": False, "error": "Ürün bulunamadı"}), 404
        
        from models import SalesModel
        tier_pricing = SalesModel.get_tier_pricing(product, quantity)
        
        unit_cost = tier_pricing['cost_price']
        unit_sale = tier_pricing['sale_price']
        total_cost = unit_cost * quantity
        total_sale = unit_sale * quantity
        total_profit = total_sale - total_cost
        profit_margin = (total_profit / total_sale * 100) if total_sale > 0 else 0
        
        return jsonify({
            "success": True,
            "quantity": quantity,
            "unit_cost_price": round(unit_cost, 2),
            "unit_sale_price": round(unit_sale, 2),
            "total_cost": round(total_cost, 2),
            "total_amount": round(total_sale, 2),
            "total_profit": round(total_profit, 2),
            "profit_margin": round(profit_margin, 2),
            "currency": product.get('currency', 'USD')
        })
    except Exception as e:
        logger.error(f"Calculate price error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@products_bp.route("/api/products", methods=["POST"])
@login_required
def api_create_product():
    """Yeni ürün ekle (tier pricing destekli)"""
    try:
        data = request.get_json()
        
        name = data.get("name")
        description = data.get("description", "")
        category = data.get("category", "")
        currency = data.get("currency", "USD")
        use_tier_pricing = data.get("use_tier_pricing", False)
        
        if not name:
            return jsonify({"success": False, "error": "Ürün adı gerekli"}), 400
        
        if use_tier_pricing:
            # Tier pricing modu
            pricing_tiers = data.get("pricing_tiers", [])
            if not pricing_tiers:
                return jsonify({"success": False, "error": "Tier pricing için en az bir fiyat basamağı gerekli"}), 400
            
            product = ProductModel.create_product(
                name=name,
                description=description,
                category=category,
                currency=currency,
                use_tier_pricing=True,
                pricing_tiers=pricing_tiers
            )
        else:
            # Basit mod
            cost_price = data.get("cost_price")
            sale_price = data.get("sale_price")
            
            if cost_price is None or sale_price is None:
                return jsonify({"success": False, "error": "Alış ve satış fiyatı gerekli"}), 400
            
            product = ProductModel.create_product(
                name=name,
                cost_price=cost_price,
                sale_price=sale_price,
                description=description,
                category=category,
                currency=currency,
                use_tier_pricing=False
            )
        
        return jsonify({
            "success": True,
            "product": product,
            "message": "Ürün eklendi"
        })
    except Exception as e:
        logger.error(f"Create product error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@products_bp.route("/api/products/<product_id>", methods=["PUT"])
@login_required
def api_update_product(product_id):
    """Ürün güncelle (tier pricing destekli)"""
    try:
        data = request.get_json()
        
        name = data.get("name")
        description = data.get("description", "")
        category = data.get("category", "")
        currency = data.get("currency", "USD")
        use_tier_pricing = data.get("use_tier_pricing", False)
        
        if not name:
            return jsonify({"success": False, "error": "Ürün adı gerekli"}), 400
        
        if use_tier_pricing:
            pricing_tiers = data.get("pricing_tiers", [])
            success = ProductModel.update_product(
                product_id=product_id,
                name=name,
                description=description,
                category=category,
                currency=currency,
                use_tier_pricing=True,
                pricing_tiers=pricing_tiers
            )
        else:
            cost_price = data.get("cost_price")
            sale_price = data.get("sale_price")
            success = ProductModel.update_product(
                product_id=product_id,
                name=name,
                cost_price=cost_price,
                sale_price=sale_price,
                description=description,
                category=category,
                currency=currency,
                use_tier_pricing=False
            )
        
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
