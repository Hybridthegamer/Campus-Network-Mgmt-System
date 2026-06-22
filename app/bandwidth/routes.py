from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, BandwidthPolicy, BandwidthUsage
from . import bandwidth_bp


@bandwidth_bp.route('/')
@login_required
def index():
    policies = BandwidthPolicy.query.all()
    page = request.args.get('page', 1, type=int)
    usage_pagination = (BandwidthUsage.query.order_by(BandwidthUsage.total_bytes.desc())
                        .paginate(page=page, per_page=20, error_out=False))
    return render_template('bandwidth/index.html', policies=policies,
                           usage_pagination=usage_pagination, usage_records=usage_pagination.items)


@bandwidth_bp.route('/policies/add', methods=['POST'])
@login_required
def add_policy():
    if not current_user.is_admin():
        flash('Administrator access required.', 'danger')
        return redirect(url_for('bandwidth.index'))
    policy_name = request.form.get('policy_name', '').strip()
    upload_cap = request.form.get('upload_cap_mbps', type=float)
    download_cap = request.form.get('download_cap_mbps', type=float)
    priority = request.form.get('priority', 5, type=int)
    target_role = request.form.get('target_role', '').strip()
    description = request.form.get('description', '').strip()
    if not policy_name or not upload_cap or not download_cap:
        flash('Policy name and bandwidth caps are required.', 'danger')
        return redirect(url_for('bandwidth.index'))
    policy = BandwidthPolicy(policy_name=policy_name, upload_cap_mbps=upload_cap,
                             download_cap_mbps=download_cap, priority=priority,
                             target_role=target_role, description=description)
    db.session.add(policy)
    db.session.commit()
    flash(f'Policy "{policy_name}" created.', 'success')
    return redirect(url_for('bandwidth.index'))


@bandwidth_bp.route('/policies/<int:policy_id>/delete', methods=['POST'])
@login_required
def delete_policy(policy_id):
    if not current_user.is_super_admin():
        return jsonify({'error': 'Super Admin required'}), 403
    policy = BandwidthPolicy.query.get_or_404(policy_id)
    name = policy.policy_name
    db.session.delete(policy)
    db.session.commit()
    flash(f'Policy "{name}" deleted.', 'success')
    return redirect(url_for('bandwidth.index'))
