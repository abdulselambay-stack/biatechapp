"""
Veri Tutarlılığı Kontrolü
MessageModel'de olan ama ChatModel'de olmayan kayıtları bulur
"""
import os
from dotenv import load_dotenv
load_dotenv()

from models import MessageModel, ChatModel
from datetime import datetime

def check_sync_issues():
    print("=" * 60)
    print("📊 VERİ TUTARLILIĞI KONTROLÜ")
    print("=" * 60)
    
    # Belirli telefon numarasını kontrol et
    target_phone = "905343713131"
    
    print(f"\n🔍 Kontrol edilen telefon: {target_phone}")
    print("-" * 60)
    
    # MessageModel'de bu telefona ait kayıtlar
    messages = list(MessageModel.get_collection().find({"phone": target_phone}))
    print(f"\n📤 MessageModel'deki kayıt sayısı: {len(messages)}")
    
    if messages:
        for msg in messages:
            print(f"   - Template: {msg.get('template_name')}")
            print(f"     Status: {msg.get('status')}")
            print(f"     Tarih: {msg.get('sent_at')}")
            print(f"     Message ID: {msg.get('_id')}")
            print()
    
    # ChatModel'de bu telefona ait kayıtlar
    chats = list(ChatModel.get_collection().find({"phone": target_phone}))
    print(f"💬 ChatModel'deki kayıt sayısı: {len(chats)}")
    
    if chats:
        for chat in chats:
            print(f"   - Direction: {chat.get('direction')}")
            print(f"     Type: {chat.get('message_type')}")
            print(f"     Content: {chat.get('content')[:50]}...")
            print(f"     Tarih: {chat.get('timestamp')}")
            print()
    
    # Tutarsızlık var mı?
    if len(messages) > 0 and len(chats) == 0:
        print("⚠️  TUTARSIZLIK BULUNDU!")
        print("   MessageModel'de kayıt VAR ama ChatModel'de YOK")
        print()
        
        # Sync önerisi
        print("🔧 ÖNERİLEN ÇÖZÜM:")
        print("   Bu kayıtları ChatModel'e eklemek için sync_to_chat.py scriptini çalıştırın")
        return True
    elif len(messages) == 0:
        print("ℹ️  MessageModel'de hiç kayıt yok")
        return False
    else:
        print("✅ Veri tutarlı - her ikisinde de kayıt var")
        return False
    
    print()

def find_all_orphaned_messages():
    """MessageModel'de olan ama ChatModel'de olmayan TÜM kayıtları bul"""
    print("\n" + "=" * 60)
    print("🔍 TÜM YETIM MESAJLARI ARANIYOR")
    print("=" * 60)
    
    # Tüm başarılı mesajları al
    all_messages = list(MessageModel.get_collection().find({
        "status": {"$in": ["sent", "delivered", "read"]}
    }))
    
    print(f"\n📊 Toplam başarılı mesaj: {len(all_messages)}")
    
    orphaned = []
    
    for msg in all_messages:
        phone = msg.get("phone")
        template_name = msg.get("template_name")
        sent_at = msg.get("sent_at")
        
        # ChatModel'de bu mesaja ait kayıt var mı?
        chat_exists = ChatModel.get_collection().find_one({
            "phone": phone,
            "direction": "outgoing",
            "message_type": "template",
            "content": {"$regex": template_name}
        })
        
        if not chat_exists:
            orphaned.append({
                "phone": phone,
                "template_name": template_name,
                "status": msg.get("status"),
                "sent_at": sent_at
            })
    
    print(f"\n⚠️  ChatModel'de OLMAYAN mesaj sayısı: {len(orphaned)}")
    
    if orphaned:
        print("\nİlk 10 yetim mesaj:")
        print("-" * 60)
        for i, msg in enumerate(orphaned[:10], 1):
            print(f"{i}. {msg['phone']} - {msg['template_name']} ({msg['status']})")
        
        if len(orphaned) > 10:
            print(f"\n... ve {len(orphaned) - 10} tane daha")
    
    return orphaned

if __name__ == "__main__":
    # Belirli telefonu kontrol et
    has_issue = check_sync_issues()
    
    # Tüm yetim mesajları bul
    orphaned = find_all_orphaned_messages()
    
    if orphaned:
        print("\n" + "=" * 60)
        print("📝 SONUÇ")
        print("=" * 60)
        print(f"⚠️  {len(orphaned)} adet mesaj ChatModel'de eksik")
        print("🔧 Çözmek için: python sync_to_chat.py")
    else:
        print("\n✅ Tüm veriler tutarlı!")
