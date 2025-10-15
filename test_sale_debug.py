#!/usr/bin/env python3
"""
Satış hatası debug scripti
"""

from models import ProductModel, SalesModel
from database import get_database
import json

print("=" * 60)
print("🔍 SATIŞ DEBUG TEST")
print("=" * 60)

# Tüm ürünleri listele
print("\n📦 Mevcut Ürünler:")
products = ProductModel.get_all_products(active_only=False)
for p in products:
    print(f"\nÜrün: {p['name']}")
    print(f"  ID: {p['_id']}")
    print(f"  Currency: {p.get('currency', 'N/A')}")
    print(f"  Tier Pricing: {p.get('use_tier_pricing', False)}")
    print(f"  Cost Price: {p.get('cost_price', 'N/A')} (type: {type(p.get('cost_price'))})")
    print(f"  Sale Price: {p.get('sale_price', 'N/A')} (type: {type(p.get('sale_price'))})")
    
    if p.get('use_tier_pricing') and p.get('pricing_tiers'):
        print(f"  Pricing Tiers:")
        for tier in p.get('pricing_tiers', []):
            print(f"    - Min: {tier.get('min_quantity')} (type: {type(tier.get('min_quantity'))})")
            print(f"      Cost: {tier.get('cost_price')} (type: {type(tier.get('cost_price'))})")
            print(f"      Sale: {tier.get('sale_price')} (type: {type(tier.get('sale_price'))})")

# Test satış
if products:
    test_product = products[0]
    print(f"\n\n🧪 Test Satış - Ürün: {test_product['name']}")
    print("=" * 60)
    
    test_quantity = 1
    print(f"Miktar: {test_quantity}")
    
    try:
        # Tier pricing test
        tier_pricing = SalesModel.get_tier_pricing(test_product, test_quantity)
        print(f"\n✅ Tier Pricing Sonucu:")
        print(f"  Cost Price: {tier_pricing['cost_price']} (type: {type(tier_pricing['cost_price'])})")
        print(f"  Sale Price: {tier_pricing['sale_price']} (type: {type(tier_pricing['sale_price'])})")
        
        # Çarpma testi
        unit_cost = float(tier_pricing['cost_price'])
        unit_sale = float(tier_pricing['sale_price'])
        
        print(f"\n🔢 Hesaplama Testi:")
        print(f"  unit_cost ({type(unit_cost)}): {unit_cost}")
        print(f"  unit_sale ({type(unit_sale)}): {unit_sale}")
        print(f"  quantity ({type(test_quantity)}): {test_quantity}")
        
        total_cost = unit_cost * test_quantity
        total_sale = unit_sale * test_quantity
        
        print(f"  total_cost: {total_cost}")
        print(f"  total_sale: {total_sale}")
        
        print("\n✅ Hesaplama başarılı!")
        
    except Exception as e:
        print(f"\n❌ HATA: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n⚠️ Hiç ürün bulunamadı!")

print("\n" + "=" * 60)
