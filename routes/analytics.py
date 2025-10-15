"""
Analytics Routes
Dashboard and statistics
"""

from flask import Blueprint, request, jsonify, render_template
from routes.auth import login_required
from models import MessageModel, ContactModel
from datetime import datetime, timedelta
import logging

analytics_bp = Blueprint('analytics', __name__)
logger = logging.getLogger(__name__)

@analytics_bp.route("/")
@login_required
def dashboard():
    """Ana sayfa - Modern dashboard"""
    return render_template("dashboard_modern.html")

@analytics_bp.route("/analytics")
@login_required
def analytics_page():
    """Analitik sayfası"""
    return render_template("analytics.html")

@analytics_bp.route("/api/analytics/stats", methods=["GET"])
@login_required
def api_analytics_stats():
    """Analytics sayfası için gerçek istatistikler"""
    try:
        # Zaman aralığı (range veya time_range parametresi)
        time_range = request.args.get('time_range') or request.args.get('range', 'all')
        now = datetime.utcnow()
        
        if time_range == 'today':
            # Bugün (UTC gece yarısından itibaren)
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == '7d':
            start_date = now - timedelta(days=7)
        elif time_range == '30d':
            start_date = now - timedelta(days=30)
        elif time_range == '90d':
            start_date = now - timedelta(days=90)
        else:  # all
            start_date = datetime(2020, 1, 1)
        
        # Mesaj istatistikleri (sent_at kullan) - SADECE BAŞARILI MESAJLAR
        messages_pipeline = [
            {"$match": {
                "sent_at": {"$gte": start_date},
                "status": {"$in": ["sent", "delivered", "read"]}  # Failed HARİÇ
            }},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        message_stats = list(MessageModel.get_collection().aggregate(messages_pipeline))
        stats_dict = {item['_id']: item['count'] for item in message_stats}
        
        # Sadece gerçek gönderilen mesajları say
        sent_messages = stats_dict.get('sent', 0)
        delivered_messages = stats_dict.get('delivered', 0)
        read_messages = stats_dict.get('read', 0)
        
        total_messages = sent_messages + delivered_messages + read_messages
        
        # Failed mesajları ayrı say (gösterim için)
        failed_messages = MessageModel.get_collection().count_documents({
            "sent_at": {"$gte": start_date},
            "status": "failed"
        })
        
        # Toplam kişi sayısı
        total_contacts = ContactModel.get_collection().count_documents({})
        
        # Başarı oranları (delivered + read)
        successful_total = delivered_messages + read_messages
        success_rate = round((successful_total / total_messages * 100), 1) if total_messages > 0 else 0
        read_rate = round((read_messages / total_messages * 100), 1) if total_messages > 0 else 0
        
        return jsonify({
            "success": True,
            "stats": {
                "total_messages": total_messages,
                "sent_messages": sent_messages,
                "delivered_messages": delivered_messages,
                "read_messages": read_messages,
                "failed_messages": failed_messages,
                "total_contacts": total_contacts,
                "success_rate": success_rate,
                "read_rate": read_rate
            }
        })
    except Exception as e:
        logger.error(f"Analytics stats error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
