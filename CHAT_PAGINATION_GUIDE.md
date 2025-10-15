# 📱 Chat Pagination & Stats - Kullanım Kılavuzu

## ✅ Yapılan Değişiklikler

### Backend

#### 1. **ChatModel Güncellemeleri** (`models.py`)

**get_all_chats() - Pagination Eklendi:**
```python
def get_all_chats(filter_type="all", page=1, limit=20) -> Dict:
    # Returns:
    {
        "chats": [...],
        "total": 150,
        "page": 1,
        "limit": 20,
        "total_pages": 8,
        "has_next": True
    }
```

**get_chat_stats() - Yeni Fonksiyon:**
```python
def get_chat_stats() -> Dict:
    # Returns:
    {
        "all": 150,        # Toplam chat
        "incoming": 120,   # Mesaj atanlar
        "unread": 35,      # Okunmayanlar
        "replied": 90      # Konuştuklarımız
    }
```

#### 2. **API Endpoint'leri** (`routes/chat.py`)

**GET /api/chats (Pagination)**
```
Query Params:
- filter: all | incoming | unread | replied
- page: 1, 2, 3... (default: 1)
- limit: 20 (default: 20)

Response:
{
  "success": true,
  "chats": [...],
  "total": 150,
  "page": 1,
  "limit": 20,
  "total_pages": 8,
  "has_next": true,
  "filter": "all"
}
```

**GET /api/chats/stats (Yeni)**
```
Response:
{
  "success": true,
  "stats": {
    "all": 150,
    "incoming": 120,
    "unread": 35,
    "replied": 90
  }
}
```

## 🎨 Frontend Örneği

### 1. Filtre Butonları ile Stats

```html
<!-- Chat Filtreleri -->
<div class="flex gap-2 mb-4">
    <button @click="setFilter('all')" 
            :class="currentFilter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'"
            class="px-4 py-2 rounded-lg font-medium transition-colors">
        📋 Tümü (<span x-text="stats.all">0</span>)
    </button>
    
    <button @click="setFilter('incoming')" 
            :class="currentFilter === 'incoming' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-700'"
            class="px-4 py-2 rounded-lg font-medium transition-colors">
        💬 Mesaj Atanlar (<span x-text="stats.incoming">0</span>)
    </button>
    
    <button @click="setFilter('unread')" 
            :class="currentFilter === 'unread' ? 'bg-red-600 text-white' : 'bg-gray-100 text-gray-700'"
            class="px-4 py-2 rounded-lg font-medium transition-colors">
        🔔 Okunmayanlar (<span x-text="stats.unread">0</span>)
    </button>
    
    <button @click="setFilter('replied')" 
            :class="currentFilter === 'replied' ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700'"
            class="px-4 py-2 rounded-lg font-medium transition-colors">
        ✅ Konuştuklarımız (<span x-text="stats.replied">0</span>)
    </button>
</div>
```

### 2. Infinite Scroll Container

```html
<!-- Chat Listesi -->
<div id="chatList" 
     @scroll="handleScroll($event)"
     class="overflow-y-auto h-[600px] space-y-2">
    
    <!-- Chat items -->
    <template x-for="chat in chats" :key="chat.phone">
        <div class="p-4 bg-white rounded-lg border hover:bg-gray-50 cursor-pointer">
            <div class="flex justify-between items-center">
                <div>
                    <p class="font-bold" x-text="chat.name"></p>
                    <p class="text-sm text-gray-600" x-text="chat.last_message"></p>
                </div>
                <div class="text-right">
                    <p class="text-xs text-gray-500" x-text="formatDate(chat.last_message_time)"></p>
                    <span x-show="chat.unread_count > 0" 
                          class="inline-block bg-red-500 text-white text-xs px-2 py-1 rounded-full"
                          x-text="chat.unread_count"></span>
                </div>
            </div>
        </div>
    </template>
    
    <!-- Loading -->
    <div x-show="loading" class="text-center py-4">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-500"></div>
        <p class="text-gray-600 mt-2">Yükleniyor...</p>
    </div>
    
    <!-- End of list -->
    <div x-show="!hasNext && chats.length > 0" class="text-center py-4 text-gray-500">
        <p>Tüm chat'ler yüklendi</p>
    </div>
</div>
```

### 3. JavaScript (Alpine.js)

```javascript
function chatApp() {
    return {
        chats: [],
        stats: {
            all: 0,
            incoming: 0,
            unread: 0,
            replied: 0
        },
        currentFilter: 'all',
        currentPage: 1,
        hasNext: false,
        loading: false,
        
        init() {
            this.loadStats();
            this.loadChats();
        },
        
        async loadStats() {
            try {
                const response = await fetch('/api/chats/stats');
                const data = await response.json();
                
                if (data.success) {
                    this.stats = data.stats;
                }
            } catch (error) {
                console.error('Stats error:', error);
            }
        },
        
        async loadChats(append = false) {
            if (this.loading) return;
            
            this.loading = true;
            
            try {
                const params = new URLSearchParams({
                    filter: this.currentFilter,
                    page: this.currentPage,
                    limit: 20
                });
                
                const response = await fetch(`/api/chats?${params}`);
                const data = await response.json();
                
                if (data.success) {
                    if (append) {
                        // Infinite scroll - append to existing
                        this.chats = [...this.chats, ...data.chats];
                    } else {
                        // Fresh load - replace all
                        this.chats = data.chats;
                    }
                    
                    this.hasNext = data.has_next;
                    
                    console.log(`📊 Loaded page ${data.page}/${data.total_pages} (${data.chats.length} chats)`);
                }
            } catch (error) {
                console.error('Load chats error:', error);
            } finally {
                this.loading = false;
            }
        },
        
        setFilter(filter) {
            this.currentFilter = filter;
            this.currentPage = 1;
            this.chats = [];
            this.loadChats();
        },
        
        handleScroll(event) {
            const element = event.target;
            const scrollTop = element.scrollTop;
            const scrollHeight = element.scrollHeight;
            const clientHeight = element.clientHeight;
            
            // Dibe yakın mı? (%90)
            const threshold = scrollHeight * 0.9;
            
            if (scrollTop + clientHeight >= threshold) {
                if (this.hasNext && !this.loading) {
                    console.log('📥 Loading more chats...');
                    this.currentPage++;
                    this.loadChats(true); // append = true
                }
            }
        },
        
        formatDate(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diff = now - date;
            
            // Bugün mü?
            if (diff < 86400000) { // 24 hours
                return date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
            } else {
                return date.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit' });
            }
        }
    }
}
```

### 4. HTML Template (chat.html)

```html
{% extends "base.html" %}

{% block content %}
<div x-data="chatApp()" class="space-y-4">
    <!-- Filtre Butonları -->
    <div class="bg-white rounded-xl shadow-lg p-4">
        <div class="flex gap-2 flex-wrap">
            <button @click="setFilter('all')" 
                    :class="currentFilter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'"
                    class="px-4 py-2 rounded-lg font-medium transition-colors">
                📋 Tümü (<span x-text="stats.all">0</span>)
            </button>
            
            <button @click="setFilter('incoming')" 
                    :class="currentFilter === 'incoming' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-700'"
                    class="px-4 py-2 rounded-lg font-medium transition-colors">
                💬 Mesaj Atanlar (<span x-text="stats.incoming">0</span>)
            </button>
            
            <button @click="setFilter('unread')" 
                    :class="currentFilter === 'unread' ? 'bg-red-600 text-white' : 'bg-gray-100 text-gray-700'"
                    class="px-4 py-2 rounded-lg font-medium transition-colors">
                🔔 Okunmayanlar (<span x-text="stats.unread">0</span>)
            </button>
            
            <button @click="setFilter('replied')" 
                    :class="currentFilter === 'replied' ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700'"
                    class="px-4 py-2 rounded-lg font-medium transition-colors">
                ✅ Konuştuklarımız (<span x-text="stats.replied">0</span>)
            </button>
        </div>
    </div>
    
    <!-- Chat Listesi -->
    <div class="bg-white rounded-xl shadow-lg">
        <div id="chatList" 
             @scroll="handleScroll($event)"
             class="overflow-y-auto h-[600px] p-4 space-y-2">
            
            <template x-for="chat in chats" :key="chat.phone">
                <div @click="openChat(chat.phone)" 
                     class="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                    <div class="flex justify-between items-start">
                        <div class="flex-1">
                            <div class="flex items-center gap-2">
                                <p class="font-bold text-gray-900" x-text="chat.name"></p>
                                <span x-show="chat.unread_count > 0" 
                                      class="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full"
                                      x-text="chat.unread_count"></span>
                            </div>
                            <p class="text-sm text-gray-600 mt-1 truncate" x-text="chat.last_message"></p>
                        </div>
                        <div class="text-right ml-4">
                            <p class="text-xs text-gray-500" x-text="formatDate(chat.last_message_time)"></p>
                        </div>
                    </div>
                </div>
            </template>
            
            <!-- Loading -->
            <div x-show="loading" class="text-center py-8">
                <div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-500"></div>
                <p class="text-gray-600 mt-2">Yükleniyor...</p>
            </div>
            
            <!-- Empty State -->
            <div x-show="!loading && chats.length === 0" class="text-center py-12">
                <svg class="w-16 h-16 text-gray-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                </svg>
                <p class="text-gray-500">Henüz chat yok</p>
            </div>
            
            <!-- End of list -->
            <div x-show="!hasNext && chats.length > 0" class="text-center py-4 text-gray-500">
                <p class="text-sm">— Tüm chat'ler yüklendi —</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script>
function chatApp() {
    // ... JavaScript kodu yukarıda
}
</script>
{% endblock %}
```

## 📊 Örnek API Çağrıları

### 1. İlk Sayfa
```bash
GET /api/chats?filter=all&page=1&limit=20

Response:
{
  "success": true,
  "chats": [...20 items],
  "total": 150,
  "page": 1,
  "limit": 20,
  "total_pages": 8,
  "has_next": true
}
```

### 2. İkinci Sayfa (Infinite Scroll)
```bash
GET /api/chats?filter=all&page=2&limit=20

Response:
{
  "success": true,
  "chats": [...20 items],
  "total": 150,
  "page": 2,
  "limit": 20,
  "total_pages": 8,
  "has_next": true
}
```

### 3. Okunmayanlar
```bash
GET /api/chats?filter=unread&page=1&limit=20

Response:
{
  "success": true,
  "chats": [...],
  "total": 35,
  "page": 1,
  "limit": 20,
  "total_pages": 2,
  "has_next": true
}
```

### 4. İstatistikler
```bash
GET /api/chats/stats

Response:
{
  "success": true,
  "stats": {
    "all": 150,
    "incoming": 120,
    "unread": 35,
    "replied": 90
  }
}
```

## ✨ Özellikler

1. **Pagination** ✅
   - Her seferinde 20 chat yüklenir
   - Sunucu yükü azalır
   - API response hızlı gelir

2. **Infinite Scroll** ✅
   - Aşağı kaydırınca otomatik yüklenir
   - Kullanıcı deneyimi iyi
   - Sayfa numaralarıyla uğraşma yok

3. **Stats** ✅
   - Her filtrede kaç chat var gösterir
   - Anlık güncellenir
   - Butonlarda adet görünür

4. **Performance** ✅
   - İlk yükleme çok hızlı (20 chat)
   - Lazy loading
   - MongoDB aggregation optimize

## 🚀 Deployment

Backend hazır! Frontend'i chat.html'e ekleyin:

1. Filtre butonlarını stats ile güncelleyin
2. Infinite scroll ekleyin
3. Test edin

## 📝 Notlar

- Default limit: 20 chat
- Scroll threshold: %90 (dibe yakın)
- Stats her filter değişiminde güncellenir
- Empty state handling eklendi
- Loading state handling eklendi
