"""
Authentication Routes
Login, logout, session management
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
from models import AdminModel
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

def login_required(f):
    """Login kontrolü için decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login sayfası"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if AdminModel.verify_login(username, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('analytics.dashboard'))
        else:
            return render_template("login.html", error="Kullanıcı adı veya şifre hatalı")
    
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    """Login API for AJAX requests"""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        if AdminModel.verify_login(username, password):
            session['logged_in'] = True
            session['username'] = username
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Kullanıcı adı veya şifre hatalı"}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@auth_bp.route("/api/logout", methods=["POST"])
def api_logout():
    """Logout API"""
    session.clear()
    return jsonify({"success": True})
