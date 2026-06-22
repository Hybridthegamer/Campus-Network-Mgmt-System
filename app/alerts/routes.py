from datetime import datetime
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Alert
from . import alerts_bp


@alerts_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    severity_filter = request.args.get('severity', '')
    type_filter = request.args.get('type', '')
    ack_filter = request.args.get('acknowledged', '')
    query = Alert.query
    if severity_filter:
        query = query.filter_by(severity=severity_filter)
    if type_filter:
        query = query.filter_by(alert_type=type_filter)
    if ack_filter == 'yes':
        query = query.filter_by(is_acknowledged=True)
    elif ack_filter == 'no':
        query = query.filter_by(is_acknowledged=False)
    pagination = query.order_by(Alert.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    unacked_count = Alert.query.filter_by(is_acknowledged=False).count()
    return render_template('alerts/index.html', pagination=pagination, alerts=pagination.items,
                           severity_filter=severity_filter, type_filter=type_filter,
                           ack_filter=ack_filter, unacked_count=unacked_count)


@alerts_bp.route('/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    alert.is_acknowledged = True
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'alert_id': alert_id})


@alerts_bp.route('/acknowledge-all', methods=['POST'])
@login_required
def acknowledge_all():
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    now = datetime.utcnow()
    Alert.query.filter_by(is_acknowledged=False).update({
        'is_acknowledged': True, 'acknowledged_by': current_user.id, 'acknowledged_at': now,
    })
    db.session.commit()
    return jsonify({'success': True})
