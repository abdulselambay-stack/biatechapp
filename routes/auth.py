"""
Authentication Routes
Login, logout, session management
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from models import AdminModel
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

def login_required(f):
    """Login kontrolü için decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route("/")
def index():
    """Ana sayfa - login kontrolü yap"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login sayfası"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if AdminModel.verify_login(username, password):
            session['user_id'] = username
            flash("✅ Giriş başarılı!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Kullanıcı adı veya şifre hatalı!", "error")
    
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    """Logout"""
    session.pop('user_id', None)
    flash("👋 Çıkış yapıldı", "info")
    return redirect(url_for('auth.login'))
