"""
Chat Routes
Chat history and messaging
"""

from flask import Blueprint, request, jsonify, render_template
from routes.auth import login_required
from models import ChatModel, ContactModel
import logging

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

@chat_bp.route("/chat")
@login_required
def chat_page():
    """Chat sayfası"""
    return render_template("chat.html")

@chat_bp.route("/api/chats", methods=["GET"])
def api_get_chats():
    """
    Tüm chat'leri getir (MongoDB, pagination)
    
    Query params:
    - filter: all (default), incoming, unread, replied
    - page: sayfa numarası (default: 1)
    - limit: sayfa başına chat sayısı (default: 20)
    """
    try:
        filter_type = request.args.get('filter', 'all')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        result = ChatModel.get_all_chats(filter_type=filter_type, page=page, limit=limit)
        
        # Her chat için contact bilgisini ekle
        for chat in result['chats']:
            contact = ContactModel.get_contact(chat['phone'])
            if contact:
                chat['name'] = contact['name']
            else:
                chat['name'] = chat['phone']
        
        return jsonify({
            "success": True,
            "chats": result['chats'],
            "total": result['total'],
            "page": result['page'],
            "limit": result['limit'],
            "total_pages": result['total_pages'],
            "has_next": result['has_next'],
            "filter": filter_type
        })
    except Exception as e:
        logger.error(f"Get chats error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chat_bp.route("/api/chats/stats", methods=["GET"])
def api_get_chat_stats():
    """
    Chat istatistiklerini getir
    Returns: {all: X, incoming: X, unread: X, replied: X}
    """
    try:
        stats = ChatModel.get_chat_stats()
        
        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Get chat stats error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chat_bp.route("/api/chat/<phone>", methods=["GET"])
def api_get_chat_history(phone):
    """Bir kişiyle olan chat geçmişini getir (MongoDB)"""
    try:
        limit = int(request.args.get("limit", 100))
        messages = ChatModel.get_chat_history(phone, limit=limit)
        
        # Mesajları okundu olarak işaretle
        ChatModel.mark_messages_as_read(phone)
        
        return jsonify({
            "success": True,
            "messages": messages
        })
    except Exception as e:
        logger.error(f"Get chat history error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chat_bp.route("/api/chat/<phone>/mark-read", methods=["POST"])
def api_mark_chat_read(phone):
    """Chat'i okundu olarak işaretle"""
    try:
        ChatModel.mark_messages_as_read(phone)
        
        return jsonify({
            "success": True,
            "message": "Mesajlar okundu olarak işaretlendi"
        })
    except Exception as e:
        logger.error(f"Mark read error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chat_bp.route("/api/chat/unread-count", methods=["GET"])
def api_get_unread_count():
    """Toplam okunmamış mesaj sayısı"""
    try:
        total = ChatModel.get_total_unread_count()
        
        return jsonify({
            "success": True,
            "unread_count": total
        })
    except Exception as e:
        logger.error(f"Get unread count error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
