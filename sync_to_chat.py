"""
MessageModel -> ChatModel Sync Script
MessageModel'de olan ama ChatModel'de olmayan kayıtları senkronize eder
"""
import os
from dotenv import load_dotenv
load_dotenv()

from models import MessageModel, ChatModel, ContactModel
from datetime import datetime

def sync_messages_to_chat():
    print("=" * 60)
    print("🔄 MESSAGEMODEL -> CHATMODEL SENKRONIZASYONU")
    print("=" * 60)
    
    # Tüm başarılı mesajları al
    all_messages = list(MessageModel.get_collection().find({
        "status": {"$in": ["sent", "delivered", "read"]}
    }))
    
    print(f"\n📊 Kontrol edilecek mesaj: {len(all_messages)}")
    
    synced_count = 0
    skipped_count = 0
    failed_count = 0
    
    for msg in all_messages:
        phone = msg.get("phone")
        template_name = msg.get("template_name")
        status = msg.get("status")
        sent_at = msg.get("sent_at")
        
        # ChatModel'de bu mesaja ait kayıt var mı?
        chat_exists = ChatModel.get_collection().find_one({
            "phone": phone,
            "direction": "outgoing",
            "message_type": "template",
            "content": {"$regex": template_name}
        })
        
        if chat_exists:
            skipped_count += 1
            continue
        
        # ChatModel'de yok, ekle
        try:
            # Contact bilgisini al
            contact = ContactModel.get_contact(phone)
            contact_name = contact.get("name", "Unknown") if contact else "Unknown"
            
            # Chat'e kaydet
            ChatModel.save_message(
                phone=phone,
                direction="outgoing",
                message_type="template",
                content=f"📤 Toplu Gönderim: {template_name}",
                media_url=None,
                timestamp=sent_at  # Orijinal gönderim tarihini koru
            )
            
            synced_count += 1
            print(f"✅ Senkronize edildi: {contact_name} ({phone}) - {template_name}")
            
        except Exception as e:
            failed_count += 1
            print(f"❌ HATA: {phone} - {template_name}: {str(e)}")
    
    print("\n" + "=" * 60)
    print("📊 SONUÇ")
    print("=" * 60)
    print(f"✅ Senkronize edildi: {synced_count}")
    print(f"⏭️  Zaten vardı (atlandı): {skipped_count}")
    print(f"❌ Hata: {failed_count}")
    print(f"📦 Toplam işlenen: {len(all_messages)}")
    
    return synced_count

def sync_single_phone(phone_number):
    """Belirli bir telefon numarasını sync et"""
    print(f"\n🔄 Tek telefon senkronizasyonu: {phone_number}")
    print("-" * 60)
    
    # Bu telefona ait tüm başarılı mesajları al
    messages = list(MessageModel.get_collection().find({
        "phone": phone_number,
        "status": {"$in": ["sent", "delivered", "read"]}
    }))
    
    if not messages:
        print(f"⚠️  {phone_number} için MessageModel'de kayıt bulunamadı")
        return 0
    
    print(f"📊 {len(messages)} adet mesaj bulundu")
    
    synced = 0
    for msg in messages:
        template_name = msg.get("template_name")
        sent_at = msg.get("sent_at")
        
        # ChatModel'de var mı?
        chat_exists = ChatModel.get_collection().find_one({
            "phone": phone_number,
            "content": {"$regex": template_name}
        })
        
        if chat_exists:
            print(f"⏭️  {template_name} - Zaten chatte var")
            continue
        
        try:
            ChatModel.save_message(
                phone=phone_number,
                direction="outgoing",
                message_type="template",
                content=f"📤 Toplu Gönderim: {template_name}",
                media_url=None,
                timestamp=sent_at
            )
            synced += 1
            print(f"✅ Senkronize: {template_name}")
        except Exception as e:
            print(f"❌ Hata: {template_name} - {str(e)}")
    
    print(f"\n✅ {synced} mesaj chatte senkronize edildi")
    return synced

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Belirli telefon sync et
        phone = sys.argv[1]
        sync_single_phone(phone)
    else:
        # Tüm mesajları sync et
        print("⚠️  TÜM MESAJLAR SENKRONIZE EDİLECEK!")
        confirm = input("Devam etmek istiyor musunuz? (evet/hayır): ")
        
        if confirm.lower() in ['evet', 'e', 'yes', 'y']:
            synced = sync_messages_to_chat()
            print(f"\n🎉 İşlem tamamlandı! {synced} mesaj senkronize edildi.")
        else:
            print("❌ İşlem iptal edildi")
    
    print("\n💡 Kullanım örnekleri:")
    print("   Tüm mesajları sync et:        python sync_to_chat.py")
    print("   Tek telefonu sync et:         python sync_to_chat.py 905343713131")
