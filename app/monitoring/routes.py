from flask import render_template, jsonify
from flask_login import login_required
from app.models import AccessPoint, NetworkLog
from . import monitoring_bp


@monitoring_bp.route('/')
@login_required
def index():
    access_points = AccessPoint.query.order_by(AccessPoint.building, AccessPoint.ap_name).all()
    recent_logs = (NetworkLog.query.order_by(NetworkLog.timestamp.desc()).limit(50).all())
    return render_template('monitoring/index.html',
                           access_points=access_points, recent_logs=recent_logs)


@monitoring_bp.route('/live-data')
@login_required
def live_data():
    aps = AccessPoint.query.all()
    data = [{'id': ap.id, 'ap_name': ap.ap_name, 'status': ap.status,
              'status_color': ap.get_status_color(), 'client_count': ap.client_count or 0,
              'channel_utilization': round(ap.channel_utilization or 0, 1),
              'uptime': ap.get_uptime_formatted(),
              'last_polled': ap.last_polled.strftime('%H:%M:%S') if ap.last_polled else 'Never'}
             for ap in aps]
    return jsonify({'access_points': data})
