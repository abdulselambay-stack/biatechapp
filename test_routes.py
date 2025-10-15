#!/usr/bin/env python3
"""
Test script to verify all routes load correctly
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment
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

print("Testing route imports...")

try:
    print("1. Testing auth blueprint...")
    from routes.auth import auth_bp
    print("   ✅ Auth blueprint OK")
    
    print("2. Testing webhook blueprint...")
    from routes.webhook import webhook_bp
    print("   ✅ Webhook blueprint OK")
    
    print("3. Testing contacts blueprint...")
    from routes.contacts import contacts_bp
    print("   ✅ Contacts blueprint OK")
    
    print("4. Testing chat blueprint...")
    from routes.chat import chat_bp
    print("   ✅ Chat blueprint OK")
    
    print("5. Testing analytics blueprint...")
    from routes.analytics import analytics_bp
    print("   ✅ Analytics blueprint OK")
    
    print("6. Testing bulk_send blueprint...")
    from routes.bulk_send import bulk_send_bp
    print("   ✅ Bulk_send blueprint OK")
    
    print("7. Testing products blueprint...")
    from routes.products import products_bp
    print("   ✅ Products blueprint OK")
    
    print("8. Testing sales blueprint...")
    from routes.sales import sales_bp
    print("   ✅ Sales blueprint OK")
    
    print("9. Testing templates blueprint...")
    from routes.templates import templates_bp
    print("   ✅ Templates blueprint OK")
    
    print("10. Testing messages blueprint...")
    from routes.messages import messages_bp
    print("   ✅ Messages blueprint OK")
    
    print("11. Testing pages blueprint...")
    from routes.pages import pages_bp
    print("   ✅ Pages blueprint OK")
    
    print("\n" + "="*60)
    print("✅ ALL BLUEPRINTS LOADED SUCCESSFULLY!")
    print("="*60)
    
    print("\nTesting Flask app creation...")
    from app import app
    
    print("\nRegistered routes:")
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{rule.endpoint:40s} {str(rule.methods):30s} {rule.rule}")
    
    for route in sorted(routes):
        print(f"  {route}")
    
    print("\n" + "="*60)
    print(f"✅ Flask app created with {len(routes)} routes!")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
