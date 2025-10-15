# 📊 Template Status API - Kullanım Kılavuzu

## ✅ Yeni Özellik: Tüm Contactların Template Durumunu Görüntüleme

### API Endpoint
```
GET /api/bulk-send/template-status?template_name=sablon_6
```

### Response Format
```json
{
  "success": true,
  "template_name": "sablon_6",
  "stats": {
    "total_contacts": 150,
    "sent": 47,
    "not_sent": 103
  },
  "contacts": [
    {
      "phone": "905370437838",
      "name": "Sami",
      "country": "TR",
      "tags": ["müşteri"],
      "sent": true,
      "status": "delivered",
      "sent_at": "2025-10-15T16:30:00",
      "source": "messages"
    },
    {
      "phone": "905324042880",
      "name": "Ozan ERGÜZ",
      "country": "TR",
      "tags": [],
      "sent": false,
      "status": "not_sent",
      "sent_at": null,
      "source": null
    }
  ]
}
```

### Field Açıklamaları

**Stats:**
- `total_contacts`: Toplam aktif kişi sayısı
- `sent`: Bu template'i almış kişi sayısı
- `not_sent`: Bu template'i almamış kişi sayısı

**Contact Fields:**
- `sent`: `true` = gönderilmiş, `false` = gönderilmemiş
- `status`: `delivered`, `read`, `sent`, `failed`, `not_sent`
- `sent_at`: Gönderim tarihi (ISO format)
- `source`: `messages` (MessageModel'den) veya `sent_templates` (Contact'tan)

### Frontend Örnek Kod

#### JavaScript/Fetch
```javascript
async function showTemplateStatus(templateName) {
  const response = await fetch(
    `/api/bulk-send/template-status?template_name=${templateName}`,
    {
      headers: {
        'Authorization': 'Bearer ' + getToken()
      }
    }
  );
  
  const data = await response.json();
  
  if (data.success) {
    console.log(`📊 ${data.stats.sent} kişiye gönderildi, ${data.stats.not_sent} kişiye gönderilmedi`);
    
    // Tabloyu doldur
    const tableBody = document.getElementById('statusTableBody');
    tableBody.innerHTML = '';
    
    data.contacts.forEach(contact => {
      const row = `
        <tr class="${contact.sent ? 'bg-green-50' : 'bg-red-50'}">
          <td>${contact.name}</td>
          <td>${contact.phone}</td>
          <td>
            ${contact.sent 
              ? `<span class="badge badge-success">✅ Gönderildi</span>` 
              : `<span class="badge badge-danger">❌ Gönderilmedi</span>`
            }
          </td>
          <td>${contact.status}</td>
          <td>${contact.sent_at || '-'}</td>
        </tr>
      `;
      tableBody.innerHTML += row;
    });
  }
}
```

#### HTML Buton Örneği
```html
<!-- Bulk Send sayfasına eklenecek -->
<div class="d-flex gap-2 mb-3">
  <button onclick="showBulkSendLogs()" class="btn btn-primary">
    📋 Gönderim Logları
  </button>
  
  <button onclick="showTemplateStatus()" class="btn btn-info">
    📊 Tüm Contactların Durumu
  </button>
</div>

<!-- Modal veya Tablo -->
<div id="templateStatusModal" class="modal">
  <div class="modal-dialog modal-xl">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">
          <span id="templateNameTitle"></span> - Contact Durumu
        </h5>
      </div>
      <div class="modal-body">
        <!-- İstatistikler -->
        <div class="row mb-3">
          <div class="col-md-4">
            <div class="card bg-primary text-white">
              <div class="card-body">
                <h6>Toplam Contact</h6>
                <h2 id="statTotal">0</h2>
              </div>
            </div>
          </div>
          <div class="col-md-4">
            <div class="card bg-success text-white">
              <div class="card-body">
                <h6>✅ Gönderildi</h6>
                <h2 id="statSent">0</h2>
              </div>
            </div>
          </div>
          <div class="col-md-4">
            <div class="card bg-danger text-white">
              <div class="card-body">
                <h6>❌ Gönderilmedi</h6>
                <h2 id="statNotSent">0</h2>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Filtreleme -->
        <div class="mb-3">
          <input type="text" id="searchContact" class="form-control" 
                 placeholder="İsim veya telefon ara..." 
                 onkeyup="filterContacts()">
        </div>
        
        <div class="mb-2">
          <button onclick="filterBySent(true)" class="btn btn-sm btn-success">
            Sadece Gönderilenleri Göster
          </button>
          <button onclick="filterBySent(false)" class="btn btn-sm btn-danger">
            Sadece Gönderilmeyenleri Göster
          </button>
          <button onclick="filterBySent(null)" class="btn btn-sm btn-secondary">
            Tümünü Göster
          </button>
        </div>
        
        <!-- Tablo -->
        <div class="table-responsive">
          <table class="table table-striped">
            <thead>
              <tr>
                <th>İsim</th>
                <th>Telefon</th>
                <th>Durum</th>
                <th>Status</th>
                <th>Gönderim Tarihi</th>
                <th>Kaynak</th>
              </tr>
            </thead>
            <tbody id="statusTableBody">
              <!-- JavaScript ile doldurulacak -->
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>
```

#### Filtreleme Fonksiyonları
```javascript
let allContacts = [];
let currentFilter = null; // null, true, false

function filterBySent(sentStatus) {
  currentFilter = sentStatus;
  renderTable();
}

function filterContacts() {
  const searchTerm = document.getElementById('searchContact').value.toLowerCase();
  
  let filtered = allContacts;
  
  // Sent/Not sent filtresi
  if (currentFilter !== null) {
    filtered = filtered.filter(c => c.sent === currentFilter);
  }
  
  // Arama filtresi
  if (searchTerm) {
    filtered = filtered.filter(c => 
      c.name.toLowerCase().includes(searchTerm) ||
      c.phone.includes(searchTerm)
    );
  }
  
  renderTable(filtered);
}

function renderTable(contacts = allContacts) {
  const tbody = document.getElementById('statusTableBody');
  tbody.innerHTML = '';
  
  contacts.forEach(contact => {
    const row = document.createElement('tr');
    row.className = contact.sent ? 'table-success' : 'table-danger';
    
    row.innerHTML = `
      <td>${contact.name}</td>
      <td>${contact.phone}</td>
      <td>
        ${contact.sent 
          ? '<span class="badge bg-success">✅ Gönderildi</span>' 
          : '<span class="badge bg-danger">❌ Gönderilmedi</span>'}
      </td>
      <td>${contact.status}</td>
      <td>${contact.sent_at || '-'}</td>
      <td>${contact.source || '-'}</td>
    `;
    
    tbody.appendChild(row);
  });
}
```

### Excel/CSV Export Özelliği
```javascript
function exportToCSV() {
  const csv = ['İsim,Telefon,Durum,Status,Gönderim Tarihi'];
  
  allContacts.forEach(c => {
    csv.push([
      c.name,
      c.phone,
      c.sent ? 'Gönderildi' : 'Gönderilmedi',
      c.status,
      c.sent_at || ''
    ].join(','));
  });
  
  const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `template-status-${new Date().toISOString()}.csv`;
  a.click();
}
```

## 🎯 Kullanım Senaryoları

1. **Durum Kontrolü**: Hangi müşterilerin kampanya mesajı aldığını görme
2. **Takip**: Gönderilmemiş kişilere manuel takip
3. **Raporlama**: Template bazlı gönderim raporu oluşturma
4. **Filtreleme**: Sadece gönderilmemiş kişilere yeni kampanya planlama

## 🔄 Test

```bash
# Postman/curl ile test
curl -X GET "http://localhost:5005/api/bulk-send/template-status?template_name=sablon_6" \
  -H "Cookie: session=..."
```

## 📝 Notlar

- Response'da gönderilmiş olanlar önce, sonra gönderilmemiş olanlar gelir
- Her biri kendi içinde isim sırasına göre sıralanır
- `source` field ile hangi kayıttan geldiği görülür (senkronizasyon takibi için)
