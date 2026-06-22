from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import db, AccessPoint, NetworkLog, Alert
from . import access_points_bp


def _require_admin():
    if not current_user.is_admin():
        flash('Administrator access required.', 'danger')
        return redirect(url_for('dashboard.index'))
    return None


@access_points_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    building_filter = request.args.get('building', '')
    query = AccessPoint.query
    if search:
        query = query.filter(
            (AccessPoint.ap_name.ilike(f'%{search}%')) |
            (AccessPoint.ip_address.ilike(f'%{search}%')) |
            (AccessPoint.location.ilike(f'%{search}%'))
        )
    if status_filter:
        query = query.filter_by(status=status_filter)
    if building_filter:
        query = query.filter_by(building=building_filter)
    pagination = query.order_by(AccessPoint.building, AccessPoint.ap_name).paginate(
        page=page, per_page=20, error_out=False)
    buildings = [b[0] for b in db.session.query(AccessPoint.building).distinct().all() if b[0]]
    return render_template('access_points/index.html', pagination=pagination,
                           access_points=pagination.items, search=search,
                           status_filter=status_filter, building_filter=building_filter,
                           buildings=buildings)


@access_points_bp.route('/<int:ap_id>')
@login_required
def detail(ap_id):
    ap = AccessPoint.query.get_or_404(ap_id)
    recent_logs = (NetworkLog.query.filter_by(ap_id=ap_id)
                   .order_by(NetworkLog.timestamp.desc()).limit(20).all())
    recent_alerts = (Alert.query.filter_by(ap_id=ap_id)
                     .order_by(Alert.created_at.desc()).limit(10).all())
    return render_template('access_points/detail.html', ap=ap,
                           recent_logs=recent_logs, recent_alerts=recent_alerts)


@access_points_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    guard = _require_admin()
    if guard:
        return guard
    if request.method == 'POST':
        ap_name = request.form.get('ap_name', '').strip()
        mac_address = request.form.get('mac_address', '').strip().upper()
        ip_address = request.form.get('ip_address', '').strip()
        building = request.form.get('building', '').strip()
        floor_ = request.form.get('floor', '').strip()
        location = request.form.get('location', '').strip()
        ssid = request.form.get('ssid', '').strip()
        vlan_id = request.form.get('vlan_id', type=int)
        channel_24ghz = request.form.get('channel_24ghz', type=int)
        channel_5ghz = request.form.get('channel_5ghz', type=int)
        tx_power = request.form.get('tx_power', type=int)
        firmware_version = request.form.get('firmware_version', '').strip()
        errors = []
        if not ap_name:
            errors.append('AP Name is required.')
        if not mac_address:
            errors.append('MAC Address is required.')
        if not ip_address:
            errors.append('IP Address is required.')
        if ap_name and AccessPoint.query.filter_by(ap_name=ap_name).first():
            errors.append(f'AP name "{ap_name}" already exists.')
        if mac_address and AccessPoint.query.filter_by(mac_address=mac_address).first():
            errors.append(f'MAC address "{mac_address}" already registered.')
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('access_points/add.html')
        ap = AccessPoint(ap_name=ap_name, mac_address=mac_address, ip_address=ip_address,
                         building=building, floor=floor_, location=location, ssid=ssid,
                         vlan_id=vlan_id, channel_24ghz=channel_24ghz, channel_5ghz=channel_5ghz,
                         tx_power=tx_power, firmware_version=firmware_version,
                         status='offline', created_at=datetime.utcnow())
        db.session.add(ap)
        db.session.commit()
        flash(f'Access Point "{ap_name}" provisioned successfully.', 'success')
        return redirect(url_for('access_points.detail', ap_id=ap.id))
    return render_template('access_points/add.html')


@access_points_bp.route('/<int:ap_id>/delete', methods=['POST'])
@login_required
def delete(ap_id):
    if not current_user.is_super_admin():
        return jsonify({'error': 'Super admin access required'}), 403
    ap = AccessPoint.query.get_or_404(ap_id)
    name = ap.ap_name
    db.session.delete(ap)
    db.session.commit()
    flash(f'Access Point "{name}" removed.', 'success')
    return redirect(url_for('access_points.index'))


@access_points_bp.route('/<int:ap_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(ap_id):
    guard = _require_admin()
    if guard:
        return guard
    ap = AccessPoint.query.get_or_404(ap_id)
    if request.method == 'POST':
        ap.building = request.form.get('building', ap.building or '').strip()
        ap.floor = request.form.get('floor', ap.floor or '').strip()
        ap.location = request.form.get('location', ap.location or '').strip()
        ap.ssid = request.form.get('ssid', ap.ssid or '').strip()
        ap.vlan_id = request.form.get('vlan_id', ap.vlan_id, type=int)
        ap.channel_24ghz = request.form.get('channel_24ghz', ap.channel_24ghz, type=int)
        ap.channel_5ghz = request.form.get('channel_5ghz', ap.channel_5ghz, type=int)
        ap.tx_power = request.form.get('tx_power', ap.tx_power, type=int)
        ap.firmware_version = request.form.get('firmware_version', ap.firmware_version or '').strip()
        db.session.commit()
        flash('Access Point updated successfully.', 'success')
        return redirect(url_for('access_points.detail', ap_id=ap.id))
    return render_template('access_points/add.html', ap=ap, edit_mode=True)
