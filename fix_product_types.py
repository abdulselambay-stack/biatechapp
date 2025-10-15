#!/usr/bin/env python3
"""
Mevcut ürünlerdeki tip sorunlarını düzelt
Tüm fiyatları float'a, quantity'leri int'e çevir
"""

import os
from dotenv import load_dotenv
from database import DatabaseManager

load_dotenv()

print("=" * 60)
print("🔧 ÜRÜN TİP DÜZELTMESİ")
print("=" * 60)

# Database bağlantısı
db = DatabaseManager().get_db()
products_collection = db['products']

# Tüm ürünleri çek
products = list(products_collection.find())
print(f"\n📦 Toplam {len(products)} ürün bulundu\n")

fixed_count = 0

for product in products:
    update_fields = {}
    changes = []
    
    # cost_price düzelt
    if 'cost_price' in product:
        old_val = product['cost_price']
        new_val = float(old_val) if old_val is not None else 0.0
        if type(old_val) != float or old_val != new_val:
            update_fields['cost_price'] = new_val
            changes.append(f"cost_price: {old_val} ({type(old_val).__name__}) → {new_val} (float)")
    
    # sale_price düzelt
    if 'sale_price' in product:
        old_val = product['sale_price']
        new_val = float(old_val) if old_val is not None else 0.0
        if type(old_val) != float or old_val != new_val:
            update_fields['sale_price'] = new_val
            changes.append(f"sale_price: {old_val} ({type(old_val).__name__}) → {new_val} (float)")
    
    # Tier pricing düzelt
    if product.get('use_tier_pricing') and product.get('pricing_tiers'):
        fixed_tiers = []
        tier_changed = False
        
        for tier in product['pricing_tiers']:
            old_tier = tier.copy()
            fixed_tier = {
                'min_quantity': int(tier.get('min_quantity', 1)),
                'cost_price': float(tier.get('cost_price', 0)),
                'sale_price': float(tier.get('sale_price', 0))
            }
            
            if (type(tier.get('min_quantity')) != int or
                type(tier.get('cost_price')) != float or
                type(tier.get('sale_price')) != float):
                tier_changed = True
            
            fixed_tiers.append(fixed_tier)
        
        if tier_changed:
            update_fields['pricing_tiers'] = fixed_tiers
            changes.append(f"pricing_tiers: {len(fixed_tiers)} tier düzeltildi")
    
    # Güncellemeleri uygula
    if update_fields:
        products_collection.update_one(
            {'_id': product['_id']},
            {'$set': update_fields}
        )
        fixed_count += 1
        
        print(f"✅ {product.get('name', 'Unknown')}")
        for change in changes:
            print(f"   - {change}")
        print()

print("=" * 60)
print(f"✅ Toplam {fixed_count} ürün düzeltildi!")
print("=" * 60)

# Sonuçları kontrol et
print("\n📊 Düzeltme Sonrası Kontrol:\n")
products_after = list(products_collection.find())

for p in products_after:
    print(f"Ürün: {p.get('name', 'Unknown')}")
    print(f"  cost_price: {p.get('cost_price')} (type: {type(p.get('cost_price')).__name__})")
    print(f"  sale_price: {p.get('sale_price')} (type: {type(p.get('sale_price')).__name__})")
    
    if p.get('use_tier_pricing') and p.get('pricing_tiers'):
        print(f"  Tier Pricing:")
        for tier in p['pricing_tiers']:
            print(f"    - min: {tier.get('min_quantity')} ({type(tier.get('min_quantity')).__name__}), "
                  f"cost: {tier.get('cost_price')} ({type(tier.get('cost_price')).__name__}), "
                  f"sale: {tier.get('sale_price')} ({type(tier.get('sale_price')).__name__})")
    print()

print("✅ Tüm ürünler kontrol edildi!")
