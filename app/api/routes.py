from datetime import datetime
from flask import jsonify, request
from flask_login import login_required, current_user
from app.models import db, AccessPoint, Alert, User, NetworkLog
from . import api_bp


@api_bp.route('/aps', methods=['GET'])
@login_required
def list_aps():
    aps = AccessPoint.query.order_by(AccessPoint.building, AccessPoint.ap_name).all()
    return jsonify({'access_points': [ap.to_dict() for ap in aps], 'total': len(aps)})


@api_bp.route('/aps/<int:ap_id>', methods=['GET'])
@login_required
def get_ap(ap_id):
    ap = AccessPoint.query.get_or_404(ap_id)
    return jsonify(ap.to_dict())


@api_bp.route('/alerts', methods=['GET'])
@login_required
def list_alerts():
    unacked_only = request.args.get('unacked', 'true').lower() == 'true'
    query = Alert.query
    if unacked_only:
        query = query.filter_by(is_acknowledged=False)
    alerts = query.order_by(Alert.created_at.desc()).limit(50).all()
    return jsonify({'alerts': [a.to_dict() for a in alerts], 'total': len(alerts)})


@api_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_alert(alert_id):
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    alert = Alert.query.get_or_404(alert_id)
    alert.is_acknowledged = True
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'alert_id': alert_id})


@api_bp.route('/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    aps = AccessPoint.query.all()
    return jsonify({
        'total_aps': len(aps),
        'online_aps': sum(1 for ap in aps if ap.status == 'online'),
        'offline_aps': sum(1 for ap in aps if ap.status == 'offline'),
        'active_alerts': Alert.query.filter_by(is_acknowledged=False).count(),
        'total_users': User.query.filter_by(is_active=True).count(),
        'total_clients': sum(ap.client_count or 0 for ap in aps),
        'timestamp': datetime.utcnow().isoformat(),
    })


@api_bp.route('/monitoring/live', methods=['GET'])
@login_required
def live_monitoring():
    aps = AccessPoint.query.all()
    return jsonify({'access_points': [ap.to_dict() for ap in aps],
                    'polled_at': datetime.utcnow().isoformat()})


@api_bp.route('/logs', methods=['GET'])
@login_required
def list_logs():
    severity = request.args.get('severity', '')
    query = NetworkLog.query
    if severity:
        query = query.filter_by(severity=severity)
    logs = query.order_by(NetworkLog.timestamp.desc()).limit(100).all()
    return jsonify({'logs': [l.to_dict() for l in logs]})
