"""
TechnoSender - WhatsApp Cloud API Bulk Messaging System
Modular Flask Application
"""

from flask import Flask, send_from_directory
from dotenv import load_dotenv
import os
import logging

# ==================== ENVIRONMENT SETUP ====================
def load_env_file():
    """Manually load .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env_file()

# ==================== FLASK APP SETUP ====================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "technoglobal-secret-key-2025")

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==================== DATABASE & MODELS ====================
from database import get_database
from models import AdminModel

# Initialize default admin
try:
    AdminModel.create_default_admin()
    logger.info("✅ Database initialized, default admin ready")
except Exception as e:
    logger.warning(f"⚠️  Admin creation warning: {e}")

# ==================== REGISTER BLUEPRINTS ====================
from routes import register_blueprints

register_blueprints(app)
logger.info("✅ All blueprints registered")

# ==================== UTILITY ROUTES ====================
@app.route("/uploads/<filename>")
def serve_upload(filename):
    """Serve uploaded files"""
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    return send_from_directory(uploads_dir, filename)

# ==================== RUN APPLICATION ====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5005))
    logger.info("=" * 60)
    logger.info("🌐 TechnoSender - WhatsApp Cloud API System")
    logger.info(f"📍 Port: {port}")
    logger.info("⚠️  Use gunicorn for production!")
    logger.info("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
