from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, User, BandwidthPolicy
from . import users_mgmt_bp


def _require_admin():
    if not current_user.is_admin():
        flash('Administrator access required.', 'danger')
        return redirect(url_for('dashboard.index'))
    return None


@users_mgmt_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.full_name.ilike(f'%{search}%')) |
            (User.department.ilike(f'%{search}%'))
        )
    if role_filter:
        query = query.filter_by(role=role_filter)
    pagination = query.order_by(User.full_name).paginate(page=page, per_page=20, error_out=False)
    return render_template('users_mgmt/index.html', pagination=pagination,
                           users=pagination.items, search=search, role_filter=role_filter)


@users_mgmt_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    guard = _require_admin()
    if guard:
        return guard
    policies = BandwidthPolicy.query.all()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'read_only')
        department = request.form.get('department', '').strip()
        phone = request.form.get('phone', '').strip()
        errors = []
        if not username:
            errors.append('Username is required.')
        if not email:
            errors.append('Email is required.')
        if not full_name:
            errors.append('Full name is required.')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if role not in ('super_admin', 'admin', 'read_only'):
            errors.append('Invalid role selected.')
        if username and User.query.filter_by(username=username).first():
            errors.append(f'Username "{username}" already taken.')
        if email and User.query.filter_by(email=email).first():
            errors.append(f'Email "{email}" already registered.')
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('users_mgmt/add.html', policies=policies)
        if role == 'super_admin' and not current_user.is_super_admin():
            flash('Only Super Admins can create Super Admin accounts.', 'danger')
            return render_template('users_mgmt/add.html', policies=policies)
        user = User(username=username, email=email, full_name=full_name,
                    role=role, department=department, phone=phone, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'User "{full_name}" created successfully.', 'success')
        return redirect(url_for('users_mgmt.index'))
    return render_template('users_mgmt/add.html', policies=policies)


@users_mgmt_bp.route('/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggle_active(user_id):
    guard = _require_admin()
    if guard:
        return guard
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('users_mgmt.index'))
    user.is_active = not user.is_active
    db.session.commit()
    state = 'activated' if user.is_active else 'deactivated'
    flash(f'User "{user.full_name}" {state}.', 'success')
    return redirect(url_for('users_mgmt.index'))


@users_mgmt_bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
def delete(user_id):
    if not current_user.is_super_admin():
        flash('Super Admin access required.', 'danger')
        return redirect(url_for('users_mgmt.index'))
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('users_mgmt.index'))
    name = user.full_name
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{name}" deleted.', 'success')
    return redirect(url_for('users_mgmt.index'))
