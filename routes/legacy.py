"""
Legacy Routes
Eski app.py'den kalan ve başka yere uymayan endpoint'ler
"""

from flask import Blueprint, request, jsonify
from routes.auth import login_required
from models import MessageModel, WebhookLogModel
import os
import json
import logging

legacy_bp = Blueprint('legacy', __name__)
logger = logging.getLogger(__name__)

@legacy_bp.route("/api/stats", methods=["GET"])
@login_required
def api_stats():
    """Dashboard istatistikleri (legacy)"""
    try:
        time_range = request.args.get('range', 'all')
        
        # Bu endpoint analytics'e yönlendirilmeli
        # Şimdilik basit stats dön
        total_messages = MessageModel.get_collection().count_documents({})
        sent = MessageModel.get_collection().count_documents({"status": "sent"})
        delivered = MessageModel.get_collection().count_documents({"status": "delivered"})
        read = MessageModel.get_collection().count_documents({"status": "read"})
        failed = MessageModel.get_collection().count_documents({"status": "failed"})
        
        return jsonify({
            "total_messages": total_messages,
            "sent": sent,
            "delivered": delivered,
            "read": read,
            "failed": failed
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({
            "total_messages": 0,
            "sent": 0,
            "delivered": 0,
            "read": 0,
            "failed": 0
        })

@legacy_bp.route("/api/recent-activity", methods=["GET"])
@login_required
def api_recent_activity():
    """Son aktiviteler"""
    try:
        limit = int(request.args.get("limit", 10))
        
        # Son gönderilen mesajları getir
        messages = list(MessageModel.get_collection()
            .find()
            .sort("sent_at", -1)
            .limit(limit))
        
        activities = []
        for msg in messages:
            activities.append({
                "type": "message",
                "phone": msg.get("phone"),
                "template_name": msg.get("template_name"),
                "status": msg.get("status"),
                "timestamp": msg.get("sent_at").isoformat() if msg.get("sent_at") else None
            })
        
        return jsonify(activities)
    except Exception as e:
        logger.error(f"Activity error: {e}")
        return jsonify([])

@legacy_bp.route("/api/webhook-logs", methods=["GET"])
@login_required
def api_get_webhook_logs():
    """Son webhook loglarını getir"""
    try:
        limit = int(request.args.get("limit", 50))
        
        # MongoDB'den getir
        logs = list(WebhookLogModel.get_collection()
            .find()
            .sort("timestamp", -1)
            .limit(limit))
        
        # JSON dosyasından da yedek getir (backward compatibility)
        log_file = "webhook_logs.json"
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    json_logs = json.load(f)
                    if isinstance(json_logs, list):
                        return jsonify({"logs": json_logs[-limit:]})
            except:
                pass
        
        # MongoDB log'larını formatla
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "timestamp": log.get("timestamp").isoformat() if log.get("timestamp") else None,
                "event_type": log.get("event_type"),
                "phone": log.get("phone"),
                "data": log.get("data", {})
            })
        
        return jsonify({"logs": formatted_logs})
    except Exception as e:
        logger.error(f"Webhook logs error: {e}")
        return jsonify({"logs": []})
