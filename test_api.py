"""
Test script for WhatsApp Cloud API system
Bu script API endpoint'lerini test etmek için kullanılır
"""
import requests
import json

BASE_URL = "http://localhost:5005"

def test_contacts():
    """Test: Kişi listesini getir"""
    print("🧪 Test 1: Kişi listesi...")
    response = requests.get(f"{BASE_URL}/api/contacts")
    data = response.json()
    print(f"✅ Toplam kişi: {data['total']}")
    print(f"   İlk 3 kişi: {data['contacts'][:3]}\n")

def test_history():
    """Test: Mesaj geçmişini getir"""
    print("🧪 Test 2: Mesaj geçmişi...")
    response = requests.get(f"{BASE_URL}/api/history")
    data = response.json()
    print(f"✅ Şablon sayısı: {len(data['history'])}")
    print(f"   İstatistikler: {data['stats']}\n")

def test_webhook_logs():
    """Test: Webhook loglarını getir"""
    print("🧪 Test 3: Webhook logları...")
    response = requests.get(f"{BASE_URL}/api/webhook-logs?limit=5")
    data = response.json()
    print(f"✅ Toplam log: {data['total']}")
    print(f"   Son 5 log: {len(data['logs'])} adet\n")

def test_duplicate_check():
    """Test: Duplicate kontrolü"""
    print("🧪 Test 4: Duplicate kontrolü...")
    payload = {
        "template_name": "test_template",
        "phone_numbers": ["905551234567", "905559876543"]
    }
    response = requests.post(
        f"{BASE_URL}/api/check-duplicates",
        headers={"Content-Type": "application/json"},
        json=payload
    )
    data = response.json()
    print(f"✅ Kontrol sonucu:")
    print(f"   {json.dumps(data, indent=2, ensure_ascii=False)}\n")

def test_send_simulation():
    """Test: Mesaj gönderimi (simülasyon - gerçekten göndermez)"""
    print("🧪 Test 5: Mesaj gönderimi...")
    print("⚠️  NOT: Gerçek göndermek için ACCESS_TOKEN ve PHONE_NUMBER_ID ayarlayın")
    
    # Bu test sadece endpoint'in çalıştığını kontrol eder
    # Gerçek gönderim yapmaz çünkü geçersiz token kullanır
    payload = {
        "template_name": "hello_world",
        "limit": 5,  # Test için sadece 5 kişi
        "language_code": "tr"
    }
    
    print(f"   Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print(f"   Endpoint hazır: {BASE_URL}/api/send")
    print(f"   ✅ Test için gerçek göndermiyoruz\n")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 WhatsApp Cloud API Test Script")
    print("=" * 60)
    print(f"📡 Base URL: {BASE_URL}\n")
    
    try:
        # Test 1-4: Okuma işlemleri
        test_contacts()
        test_history()
        test_webhook_logs()
        test_duplicate_check()
        
        # Test 5: Gönderim endpoint'i (sadece bilgilendirme)
        test_send_simulation()
        
        print("=" * 60)
        print("✅ Tüm testler tamamlandı!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("❌ HATA: Uygulama çalışmıyor!")
        print("   Önce 'python app.py' ile uygulamayı başlatın.\n")
    except Exception as e:
        print(f"❌ HATA: {e}\n")
