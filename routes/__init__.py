"""
Routes Package
Blueprint'leri organize eder
"""

from flask import Blueprint

def register_blueprints(app):
    """Tüm blueprint'leri app'e kaydet"""
    
    from .auth import auth_bp
    from .webhook import webhook_bp
    from .contacts import contacts_bp
    from .chat import chat_bp
    from .analytics import analytics_bp
    from .bulk_send import bulk_send_bp
    from .products import products_bp
    from .sales import sales_bp
    from .templates import templates_bp
    from .messages import messages_bp
    from .pages import pages_bp
    
    # Blueprint'leri kaydet
    app.register_blueprint(auth_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(bulk_send_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(pages_bp)
    
    print("✅ All blueprints registered")
