"""
Pages Routes
Miscellaneous page routes
"""

from flask import Blueprint, render_template
from routes.auth import login_required

pages_bp = Blueprint('pages', __name__)

@pages_bp.route("/campaigns")
@login_required
def campaigns_page():
    """Kampanyalar sayfası"""
    return render_template("campaigns.html")

@pages_bp.route("/settings")
@login_required
def settings_page():
    """Ayarlar sayfası"""
    return render_template("settings.html")

@pages_bp.route("/template-management")
@login_required
def template_management():
    """Şablon yönetimi sayfası"""
    return render_template("template_management.html")
