#!/usr/bin/env python3
"""
Template'ler için default image ID'lerini kaydet
"""

import os
import sys

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

load_env_file()

from models import TemplateSettingsModel

# Default image ID'leri
DEFAULT_IMAGE_IDS = {
    "sablon_6": "780517088218949"
    # Buraya yeni template'ler eklenebilir
}

def set_default_image_ids():
    """Default image ID'lerini kaydet"""
    print("🖼️  Default image ID'leri kaydediliyor...\n")
    
    for template_name, image_id in DEFAULT_IMAGE_IDS.items():
        success = TemplateSettingsModel.set_header_image_id(template_name, image_id)
        
        if success:
            print(f"✅ {template_name}: {image_id}")
        else:
            print(f"❌ {template_name}: Kaydetme başarısız")
    
    print("\n✅ Tamamlandı!")

if __name__ == "__main__":
    try:
        set_default_image_ids()
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
