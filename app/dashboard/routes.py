from flask import render_template
from flask_login import login_required
from app.models import AccessPoint, Alert, User, NetworkLog, BandwidthUsage
from . import dashboard_bp


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    total_aps = AccessPoint.query.count()
    online_aps = AccessPoint.query.filter_by(status='online').count()
    offline_aps = AccessPoint.query.filter_by(status='offline').count()
    degraded_aps = AccessPoint.query.filter_by(status='degraded').count()
    total_users = User.query.filter_by(is_active=True).count()
    active_alerts = Alert.query.filter_by(is_acknowledged=False).count()
    critical_alerts = Alert.query.filter_by(is_acknowledged=False, severity='critical').count()
    access_points = AccessPoint.query.order_by(AccessPoint.building, AccessPoint.ap_name).all()
    recent_alerts = (Alert.query
                     .filter_by(is_acknowledged=False)
                     .order_by(Alert.created_at.desc())
                     .limit(8).all())
    recent_logs = (NetworkLog.query
                   .order_by(NetworkLog.timestamp.desc())
                   .limit(10).all())
    total_clients = sum(ap.client_count or 0 for ap in access_points)
    top_usage = (BandwidthUsage.query
                 .order_by(BandwidthUsage.total_bytes.desc())
                 .limit(10).all())
    return render_template(
        'dashboard/index.html',
        total_aps=total_aps, online_aps=online_aps, offline_aps=offline_aps,
        degraded_aps=degraded_aps, total_users=total_users,
        active_alerts=active_alerts, critical_alerts=critical_alerts,
        access_points=access_points, recent_alerts=recent_alerts,
        recent_logs=recent_logs, total_clients=total_clients, top_usage=top_usage,
    )
