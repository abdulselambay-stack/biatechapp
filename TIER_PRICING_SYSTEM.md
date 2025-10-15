# 💰 Tier Pricing (Kademeli Fiyatlandırma) Sistemi

## ✅ Yapılan Geliştirmeler

### 🎯 Özellikler

1. **Tier Pricing (Kademeli Fiyatlandırma)**
   - 1 adet, 20 adet, 100+ adet gibi farklı fiyat basamakları
   - Her basamakta farklı alış ve satış fiyatı
   - Otomatik fiyat hesaplama (miktara göre)

2. **Basit Mod**
   - Tek alış/satış fiyatı
   - Klasik ürün girişi

3. **USD Para Birimi**
   - Default: USD ($)
   - TL (₺) desteği de mevcut
   - Currency bazlı istatistikler

4. **Akıllı Satış**
   - Miktar girildiğinde otomatik fiyat hesaplama
   - Tier'a göre doğru fiyat seçimi
   - Dinamik kar hesaplama

## 📊 Ürün Yapısı

### Tier Pricing Modu

```json
{
  "name": "iPhone 14 Pro Max 20W",
  "currency": "USD",
  "use_tier_pricing": true,
  "pricing_tiers": [
    {
      "min_quantity": 1,
      "cost_price": 250,
      "sale_price": 250
    },
    {
      "min_quantity": 20,
      "cost_price": 2.5,
      "sale_price": 3
    },
    {
      "min_quantity": 100,
      "cost_price": 2,
      "sale_price": 2.5
    }
  ]
}
```

### Basit Mod

```json
{
  "name": "AirPods Pro 2",
  "currency": "USD",
  "use_tier_pricing": false,
  "cost_price": 550,
  "sale_price": 550
}
```

## 🎨 Kullanım Örnekleri

### Örnek 1: iPhone 14 Pro Max 20W

**Ürün Bilgileri:**
- **1 ADET:** Satış: $250, Alış: $250, USB: $100
- **20 ADET:** Satış: $3/adet, Alış: $2.5/adet, USB: $1/adet  
- **100+ ADET:** Satış: $2.5/adet, Alış: $2/adet, USB: $0.80/adet

**Tier Pricing Girişi:**
```javascript
{
  pricing_tiers: [
    { min_quantity: 1, cost_price: 250, sale_price: 250 },
    { min_quantity: 20, cost_price: 2.5, sale_price: 3 },
    { min_quantity: 100, cost_price: 2, sale_price: 2.5 }
  ]
}
```

**Satış Senaryoları:**
- **23 adet satış:** 23 x $3 = $69 (tier: 20 adet)
- **5 adet satış:** 5 x $250 = $1,250 (tier: 1 adet)
- **150 adet satış:** 150 x $2.5 = $375 (tier: 100 adet)

### Örnek 2: Mi 67W Şarj Cihazı

**Ürün Bilgileri:**
- **1 ADET:** Satış: $350, Alış: $300
- **20 ADET:** Satış: $3.75/adet, Alış: $3/adet
- **100+ ADET:** Satış: $3/adet, Alış: $2.5/adet

```javascript
{
  name: "Mi 67W",
  currency: "USD",
  use_tier_pricing: true,
  pricing_tiers: [
    { min_quantity: 1, cost_price: 300, sale_price: 350 },
    { min_quantity: 20, cost_price: 3, sale_price: 3.75 },
    { min_quantity: 100, cost_price: 2.5, sale_price: 3 }
  ]
}
```

## 🔧 API Endpoints

### 1. Ürün Oluşturma (Tier Pricing)

**POST** `/api/products`

```json
{
  "name": "iPhone 14 Pro Max 20W",
  "currency": "USD",
  "use_tier_pricing": true,
  "pricing_tiers": [
    { "min_quantity": 1, "cost_price": 250, "sale_price": 250 },
    { "min_quantity": 20, "cost_price": 2.5, "sale_price": 3 },
    { "min_quantity": 100, "cost_price": 2, "sale_price": 2.5 }
  ],
  "description": "iPhone için 20W hızlı şarj cihazı",
  "category": "Şarj Cihazları"
}
```

### 2. Ürün Oluşturma (Basit Mod)

**POST** `/api/products`

```json
{
  "name": "AirPods Pro 2",
  "currency": "USD",
  "use_tier_pricing": false,
  "cost_price": 550,
  "sale_price": 550,
  "description": "Apple AirPods Pro 2. Nesil"
}
```

### 3. Fiyat Hesaplama

**POST** `/api/products/{product_id}/calculate`

```json
{
  "quantity": 23
}
```

**Response:**
```json
{
  "success": true,
  "quantity": 23,
  "unit_cost_price": 2.5,
  "unit_sale_price": 3,
  "total_cost": 57.5,
  "total_amount": 69,
  "total_profit": 11.5,
  "profit_margin": 16.67,
  "currency": "USD"
}
```

### 4. Satış Oluşturma

**POST** `/api/sales`

```json
{
  "phone": "905551234567",
  "customer_name": "Ahmet Yılmaz",
  "product_id": "65abc123...",
  "quantity": 23,
  "notes": "Toplu sipariş"
}
```

**Response:**
```json
{
  "success": true,
  "sale": {
    "_id": "...",
    "customer_name": "Ahmet Yılmaz",
    "product_name": "iPhone 14 Pro Max 20W",
    "quantity": 23,
    "unit_cost_price": 2.5,
    "unit_sale_price": 3,
    "total_cost": 57.5,
    "total_amount": 69,
    "total_profit": 11.5,
    "profit_margin": 16.67,
    "currency": "USD"
  }
}
```

### 5. Satış İstatistikleri (Currency Bazlı)

**GET** `/api/sales/stats`

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_sales_count": 45,
    "total_quantity": 1250,
    "by_currency": {
      "USD": {
        "total_amount": 5420.50,
        "total_profit": 1230.25,
        "total_cost": 4190.25,
        "count": 40,
        "avg_sale": 135.51,
        "avg_profit": 30.76
      },
      "TRY": {
        "total_amount": 15000,
        "total_profit": 3500,
        "total_cost": 11500,
        "count": 5,
        "avg_sale": 3000,
        "avg_profit": 700
      }
    }
  }
}
```

## 🎨 Frontend - Satış Modal

### Özellikler

1. **Ürün Seçimi**
   - Dropdown'da currency ile birlikte fiyat gösterimi
   - Örn: "iPhone 14 Pro Max 20W - $250"

2. **Tier Pricing Göstergesi**
   - Kademeli fiyatlandırma aktif olduğunda mavi bilgi kutusu
   - "⚡ Kademeli fiyatlandırma aktif - Miktar girdiğinizde fiyat otomatik hesaplanır"

3. **Otomatik Fiyat Hesaplama**
   - Miktar değişince API çağrısı
   - Doğru tier'dan fiyat çekilir
   - Birim fiyat, toplam, kar dinamik güncellenir

4. **Bilgi Gösterimi**
   - Birim Satış: $3.00
   - Birim Alış: $2.50
   - Birim Kar: $0.50
   - Kar Marjı: 16.67%
   - Miktar: 23 adet
   - Toplam Maliyet: $57.50
   - **Toplam Tutar: $69.00**
   - **Toplam Kar: $11.50**

5. **Currency Desteği**
   - USD: $ sembolü
   - TRY: ₺ sembolü

### JavaScript Fonksiyonlar

```javascript
// Fiyat hesaplama (tier pricing API)
async updateSaleCalculation() {
    const response = await fetch(`/api/products/${product._id}/calculate`, {
        method: 'POST',
        body: JSON.stringify({ quantity: this.saleData.quantity })
    });
    const data = await response.json();
    this.saleCalculation = data; // Tüm fiyat bilgilerini güncelle
}

// Currency formatı
getCurrencySymbol(currency) {
    return currency === 'USD' ? '$' : '₺';
}

formatCurrency(amount, currency) {
    const symbol = this.getCurrencySymbol(currency || 'USD');
    return `${symbol}${parseFloat(amount).toFixed(2)}`;
}
```

## 📊 Tier Pricing Mantığı

### Algoritma

```python
def get_tier_pricing(product, quantity):
    if not product.use_tier_pricing:
        return {
            'cost_price': product.cost_price,
            'sale_price': product.sale_price
        }
    
    # Tier'ları büyükten küçüğe sırala
    tiers = sorted(product.pricing_tiers, 
                   key=lambda x: x['min_quantity'], 
                   reverse=True)
    
    # Uygun tier'ı bul
    for tier in tiers:
        if quantity >= tier['min_quantity']:
            return {
                'cost_price': tier['cost_price'],
                'sale_price': tier['sale_price']
            }
    
    # Hiçbiri uymazsa ilk tier
    return {
        'cost_price': product.cost_price,
        'sale_price': product.sale_price
    }
```

### Örnek Hesaplama

**Ürün:** iPhone 14 Pro Max 20W  
**Miktar:** 23 adet

**Tier'lar:**
- 100+ adet: $2.50 / $2.00 ❌ (23 < 100)
- 20 adet: $3.00 / $2.50 ✅ (23 >= 20)
- 1 adet: $250 / $250 (atlandı)

**Seçilen Tier:** 20 adet  
**Birim Satış:** $3.00  
**Birim Alış:** $2.50  
**Toplam:** 23 x $3.00 = $69.00  
**Maliyet:** 23 x $2.50 = $57.50  
**Kar:** $69.00 - $57.50 = $11.50

## 🎯 Kullanım Senaryoları

### Senaryo 1: Tek Ürün Satışı (Basit Mod)

**Ürün:** AirPods Pro 2  
**Fiyat:** $550 (sabit)  
**Satış:** 1 adet  
**Sonuç:** $550

### Senaryo 2: Toplu Satış (Tier Pricing)

**Ürün:** iPhone 14 Pro Max 20W  
**Satış:** 150 adet  
**Tier:** 100+ adet ($2.50/adet)  
**Sonuç:** 150 x $2.50 = $375

### Senaryo 3: Karma Satış

**Ürün:** Mi 67W  
**İlk Satış:** 15 adet → 15 x $350 = $5,250 (tier: 1 adet)  
**İkinci Satış:** 25 adet → 25 x $3.75 = $93.75 (tier: 20 adet)

## ✨ Avantajlar

1. **Esneklik:** Hem basit hem tier pricing
2. **Otomatik:** Miktar gir, fiyat hesaplansın
3. **Doğru Fiyat:** Her zaman doğru tier seçilir
4. **Multi-Currency:** USD ve TL desteği
5. **İstatistik:** Currency bazlı raporlama
6. **UX:** Kullanıcı dostu, anlık feedback

## 🔄 Workflow

1. **Ürün Ekleme:**
   - Tier pricing mi yoksa basit mod mu seç
   - Fiyat basamaklarını gir
   - Kaydet

2. **Satış:**
   - Ürün seç
   - Miktar gir → Otomatik fiyat hesaplansın
   - Kar, toplam görüntülen
   - Kaydet

3. **İstatistik:**
   - USD ve TL ayrı ayrı görüntülenir
   - Toplam ciro, kar, ortalamalar

## 📝 Notlar

- Default currency: **USD**
- Tier pricing optional (basit mod da var)
- Fiyatlar 2 ondalık basamak
- Kar marjı % olarak hesaplanır
- İstatistikler currency bazlı gruplanır

## 🎉 Sonuç

Artık:
- ✅ Kademeli fiyatlandırma yapabilirsiniz
- ✅ 1 adet, 20 adet, 100+ adet farklı fiyatlar
- ✅ Otomatik fiyat hesaplama
- ✅ USD/TL desteği
- ✅ Akıllı tier seçimi
- ✅ Detaylı istatistikler

**Sistem tamamen çalışır durumda!** 🚀
