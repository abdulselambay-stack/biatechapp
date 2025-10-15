#!/usr/bin/env python3
"""
Eski template gönderim verilerini MongoDB'ye aktarma scripti
Usage: python bulk_update_old_templates.py
"""

import os
import sys
from datetime import datetime

# .env dosyasını yükle
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✅ .env dosyası yüklendi: {env_path}")
    else:
        print(f"⚠️  .env dosyası bulunamadı: {env_path}")

# .env'i yükle
load_env_file()

# Database'i import et
from database import get_database

# Eski sablon_6 gönderim listesi
OLD_TEMPLATE_DATA = {
    "sablon_6": [
        "905352656789",
        "905340120000",
        "905347043771",
        "905316671019",
        "905327868071",
        "905340444532",
        "905387831577",
        "905336224546",
        "905523811212",
        "905345400313",
        "905322152573",
        "905395472121",
        "905334183135",
        "905393921617",
        "905438145656",
        "905389315599",
        "905073178383",
        "905330450047",
        "905326266021",
        "905465472164",
        "905384106113",
        "905362244001",
        "905362681617",
        "905396195964",
        "905352937714",
        "905398641211",
        "905356874321",
        "905452256898",
        "905379341229",
        "905334035310",
        "905334117858",
        "905385144334",
        "905305215538",
        "905541712121",
        "905352043007",
        "905055861414",
        "905393304947",
        "905343713131",
        "905366097375",
        "905437750032",
        "905494813421",
        "905317878856",
        "905070097979",
        "905457444973",
        "905327496908",
        "905358166487",
        "905366105924",
        "905373557707",
        "905326791245",
        "905523248221",
        "905528506023",
        "905363714315",
        "905402264646",
        "905541765030",
        "905309594529",
        "905394005941",
        "905382968305",
        "905418477369",
        "905333695723",
        "905357980321",
        "905353062002",
        "905419437467",
        "905455406650",
        "905342093838",
        "905379768098",
        "905312522220",
        "905331357120",
        "905350777121",
        "905377710864",
        "905326679469",
        "905532798787",
        "905529229466",
        "905466221997",
        "905303051413",
        "905322710589",
        "905056502550",
        "905425835248",
        "905327494919",
        "905394426988",
        "905070994444",
        "905071294444",
        "905394800413",
        "905323425097",
        "905467263536",
        "905061150597",
        "905357294632",
        "905416494994",
        "905458042323",
        "905312962121",
        "905316642121",
        "905399379696",
        "905322314382",
        "905069694949",
        "905393607378",
        "905522444949",
        "905456673547",
        "905324611600",
        "905336180088",
        "905452501394",
        "905330568807",
        "905365989999",
        "905469410897",
        "905340313413",
        "905348314836",
        "905415053681",
        "905313227978",
        "905304978301",
        "905324835041",
        "905464805949",
        "905438421161",
        "905396999690",
        "905308672192",
        "905301269194",
        "905524547158",
        "905435014359",
        "905327181237",
        "905323492300",
        "905364071169",
        "905364736521",
        "905364073593",
        "905372354465",
        "905072070777",
        "905550124037",
        "905393480538",
        "905330973729",
        "905453533565",
        "905378305521",
        "905437240606",
        "905418836769",
        "905307315001",
        "905354055454",
        "905305794810",
        "905336854936",
        "905530638071",
        "905353464880",
        "905393126022",
        "905375202223",
        "905519390321",
        "905334045602",
        "905425223448",
        "905358231796",
        "905331996447",
        "905379250624",
        "905303865422",
        "905359700153",
        "905529345283",
        "905340717632",
        "905301861980",
        "905446396351",
        "905375882940"
    ]
}


def update_sent_templates():
    """Eski template verilerini MongoDB'ye aktar"""
    db = get_database()
    contacts_collection = db['contacts']
    
    print("🚀 Template geçmişi güncelleme başlatılıyor...\n")
    
    total_updated = 0
    total_not_found = 0
    
    for template_name, phone_list in OLD_TEMPLATE_DATA.items():
        print(f"📝 Template: {template_name}")
        print(f"   Toplam numara: {len(phone_list)}")
        
        updated = 0
        not_found = 0
        
        for phone in phone_list:
            # Farklı formatları dene
            formats_to_try = []
            
            # Orijinal numara (905551234567)
            base_phone = phone.replace('+', '')
            
            # Farklı formatlar
            formats_to_try.append(f"+{base_phone}")           # +905551234567
            formats_to_try.append(base_phone)                  # 905551234567
            formats_to_try.append(f"+90{base_phone[2:]}")     # +905551234567
            formats_to_try.append(f"90{base_phone[2:]}")      # 905551234567
            
            # Her formatı dene
            found = False
            for format_phone in formats_to_try:
                result = contacts_collection.update_one(
                    {"phone": format_phone},
                    {
                        "$addToSet": {"sent_templates": template_name},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
                
                if result.matched_count > 0:
                    updated += 1
                    found = True
                    print(f"   ✅ Bulundu: {format_phone}")
                    break
            
            if not found:
                not_found += 1
                print(f"   ⚠️  Bulunamadı: {phone} (denendi: {', '.join(formats_to_try)})")
        
        print(f"   ✅ Güncellenen: {updated}")
        print(f"   ❌ Bulunamayan: {not_found}\n")
        
        total_updated += updated
        total_not_found += not_found
    
    print("=" * 50)
    print(f"✅ TAMAMLANDI!")
    print(f"   Toplam güncellenen: {total_updated}")
    print(f"   Toplam bulunamayan: {total_not_found}")
    print("=" * 50)


if __name__ == "__main__":
    try:
        update_sent_templates()
    except Exception as e:
        print(f"❌ HATA: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
