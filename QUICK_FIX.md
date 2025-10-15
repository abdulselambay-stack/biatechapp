# 🔧 Satış Hatası - Hızlı Çözüm

## ❌ Hata
```
{"error":"can't multiply sequence by non-int of type 'float'","success":false}
```

## ✅ Yapılan Düzeltmeler

### 1. `models.py` - create_sale()
```python
# Quantity'yi int'e çevir (API'den string gelebilir)
quantity = int(quantity) if quantity else 1

# Fiyatları açıkça float'a çevir
unit_cost = float(tier_pricing['cost_price'])
unit_sale = float(tier_pricing['sale_price'])
```

### 2. `routes/sales.py` - api_create_sale()
```python
# API route'unda da int'e çevir
quantity = int(quantity) if quantity else 1

# Detaylı log ekledik
logger.info(f"Creating sale - phone: {phone}, product: {product_id}, quantity: {quantity} (type: {type(quantity)})")
```

## 🧪 Test

### Yöntem 1: Chat'ten Test
1. Flask uygulamasını çalıştır
2. Chat aç → Satış yap
3. Terminal loglarına bak - şunu göreceksin:
   ```
   Creating sale - phone: 9055... product: 67... quantity: 1 (type: <class 'int'>)
   ```

### Yöntem 2: API ile Direkt Test

**Basit Ürün Ekle:**
```bash
curl -X POST http://localhost:5000/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Ürün",
    "currency": "USD",
    "use_tier_pricing": false,
    "cost_price": 10,
    "sale_price": 15
  }'
```

**Satış Yap:**
```bash
curl -X POST http://localhost:5000/api/sales \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "905551234567",
    "customer_name": "Test Müşteri",
    "product_id": "PRODUCT_ID_BURAYA",
    "quantity": 5,
    "notes": "Test satış"
  }'
```

## 🔍 Sorun Devam Ederse

### Kontrol 1: Veritabanındaki Ürünler
MongoDB'de ürünlerin `cost_price` ve `sale_price` değerlerinin **number** tipinde olması lazım, **string** değil.

**Düzeltme (MongoDB shell):**
```javascript
db.products.updateMany(
  {},
  [{
    $set: {
      cost_price: { $toDouble: "$cost_price" },
      sale_price: { $toDouble: "$sale_price" }
    }
  }]
)
```

### Kontrol 2: Tier Pricing'li Ürünler
```javascript
db.products.find({ use_tier_pricing: true }).forEach(product => {
  if (product.pricing_tiers) {
    product.pricing_tiers = product.pricing_tiers.map(tier => ({
      min_quantity: parseInt(tier.min_quantity),
      cost_price: parseFloat(tier.cost_price),
      sale_price: parseFloat(tier.sale_price)
    }));
    db.products.updateOne(
      { _id: product._id },
      { $set: { pricing_tiers: product.pricing_tiers } }
    );
  }
});
```

## 📝 Ne Değişti?

| Dosya | Değişiklik |
|-------|-----------|
| `models.py` | ✅ quantity → int(), unit_cost/unit_sale → float() |
| `routes/sales.py` | ✅ quantity → int(), detaylı logging |

## 🎯 Sonuç

Artık:
- ✅ Quantity string olarak gelse bile int'e çevriliyor
- ✅ Fiyatlar açıkça float'a çevriliyor
- ✅ Detaylı log var - nereden geldiğini görebilirsin

**Uygulamayı yeniden başlat ve tekrar dene!**
