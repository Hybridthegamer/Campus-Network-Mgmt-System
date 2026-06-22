from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.Enum('super_admin', 'admin', 'read_only'), nullable=False, default='read_only')
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    devices = db.relationship('Device', backref='owner', lazy='dynamic', foreign_keys='Device.user_id')
    bandwidth_usages = db.relationship('BandwidthUsage', backref='user', lazy='dynamic')
    acknowledged_alerts = db.relationship('Alert', backref='acknowledger', lazy='dynamic',
                                           foreign_keys='Alert.acknowledged_by')

    def set_password(self, password):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def is_super_admin(self):
        return self.role == 'super_admin'

    def is_admin(self):
        return self.role in ('super_admin', 'admin')

    def is_read_only(self):
        return self.role == 'read_only'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'department': self.department,
            'phone': self.phone,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    mac_address = db.Column(db.String(17), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(15))
    device_name = db.Column(db.String(100))
    device_type = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    os_type = db.Column(db.String(50))
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_authorized = db.Column(db.Boolean, default=True)
    vlan_id = db.Column(db.Integer)

    # Relationships
    bandwidth_usages = db.relationship('BandwidthUsage', backref='device', lazy='dynamic')
    network_logs = db.relationship('NetworkLog', backref='device', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'mac_address': self.mac_address,
            'ip_address': self.ip_address,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'user_id': self.user_id,
            'os_type': self.os_type,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'is_authorized': self.is_authorized,
            'vlan_id': self.vlan_id,
        }

    def __repr__(self):
        return f'<Device {self.mac_address}>'


class AccessPoint(db.Model):
    __tablename__ = 'access_points'

    id = db.Column(db.Integer, primary_key=True)
    ap_name = db.Column(db.String(100), unique=True, nullable=False)
    mac_address = db.Column(db.String(17), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(15), nullable=False)
    location = db.Column(db.String(200))
    building = db.Column(db.String(100))
    floor = db.Column(db.String(20))
    status = db.Column(db.Enum('online', 'offline', 'degraded'), default='offline', nullable=False)
    channel_24ghz = db.Column(db.Integer)
    channel_5ghz = db.Column(db.Integer)
    tx_power = db.Column(db.Integer)
    client_count = db.Column(db.Integer, default=0)
    channel_utilization = db.Column(db.Float, default=0.0)
    uptime_seconds = db.Column(db.BigInteger, default=0)
    firmware_version = db.Column(db.String(50))
    ssid = db.Column(db.String(100))
    vlan_id = db.Column(db.Integer)
    last_polled = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    network_logs = db.relationship('NetworkLog', backref='access_point', lazy='dynamic')
    alerts = db.relationship('Alert', backref='access_point', lazy='dynamic',
                              foreign_keys='Alert.ap_id')
    rogue_aps = db.relationship('RogueAP', backref='detected_by_ap', lazy='dynamic',
                                 foreign_keys='RogueAP.detected_by_ap_id')

    def get_status_color(self):
        if self.status == 'online':
            return 'success'
        elif self.status == 'degraded':
            return 'warning'
        return 'danger'

    def get_uptime_formatted(self):
        if not self.uptime_seconds:
            return '0s'
        seconds = int(self.uptime_seconds)
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        if days > 0:
            return f'{days}d {hours}h {minutes}m'
        elif hours > 0:
            return f'{hours}h {minutes}m'
        return f'{minutes}m'

    def to_dict(self):
        return {
            'id': self.id,
            'ap_name': self.ap_name,
            'mac_address': self.mac_address,
            'ip_address': self.ip_address,
            'location': self.location,
            'building': self.building,
            'floor': self.floor,
            'status': self.status,
            'status_color': self.get_status_color(),
            'channel_24ghz': self.channel_24ghz,
            'channel_5ghz': self.channel_5ghz,
            'tx_power': self.tx_power,
            'client_count': self.client_count,
            'channel_utilization': self.channel_utilization,
            'uptime_seconds': self.uptime_seconds,
            'uptime_formatted': self.get_uptime_formatted(),
            'firmware_version': self.firmware_version,
            'ssid': self.ssid,
            'vlan_id': self.vlan_id,
            'last_polled': self.last_polled.isoformat() if self.last_polled else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<AccessPoint {self.ap_name} ({self.status})>'


class BandwidthPolicy(db.Model):
    __tablename__ = 'bandwidth_policies'

    id = db.Column(db.Integer, primary_key=True)
    policy_name = db.Column(db.String(100), unique=True, nullable=False)
    upload_cap_mbps = db.Column(db.Float, nullable=False)
    download_cap_mbps = db.Column(db.Float, nullable=False)
    priority = db.Column(db.Integer, default=5)
    target_role = db.Column(db.String(50))
    description = db.Column(db.Text)

    # Relationships
    bandwidth_usages = db.relationship('BandwidthUsage', backref='policy', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'policy_name': self.policy_name,
            'upload_cap_mbps': self.upload_cap_mbps,
            'download_cap_mbps': self.download_cap_mbps,
            'priority': self.priority,
            'target_role': self.target_role,
            'description': self.description,
        }

    def __repr__(self):
        return f'<BandwidthPolicy {self.policy_name}>'


class BandwidthUsage(db.Model):
    __tablename__ = 'bandwidth_usage'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=True)
    upload_bytes = db.Column(db.BigInteger, default=0)
    download_bytes = db.Column(db.BigInteger, default=0)
    total_bytes = db.Column(db.BigInteger, default=0)
    policy_id = db.Column(db.Integer, db.ForeignKey('bandwidth_policies.id'), nullable=True)
    cap_upload_mbps = db.Column(db.Float)
    cap_download_mbps = db.Column(db.Float)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    is_cap_exceeded = db.Column(db.Boolean, default=False)

    def get_upload_mb(self):
        return round(self.upload_bytes / (1024 * 1024), 2)

    def get_download_mb(self):
        return round(self.download_bytes / (1024 * 1024), 2)

    def get_total_mb(self):
        return round(self.total_bytes / (1024 * 1024), 2)

    def get_usage_percent(self):
        if not self.cap_download_mbps:
            return 0
        cap_bytes = self.cap_download_mbps * 1024 * 1024 * 3600  # per hour
        if cap_bytes == 0:
            return 0
        return min(100, round((self.download_bytes / cap_bytes) * 100, 1))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'device_id': self.device_id,
            'upload_bytes': self.upload_bytes,
            'download_bytes': self.download_bytes,
            'total_bytes': self.total_bytes,
            'upload_mb': self.get_upload_mb(),
            'download_mb': self.get_download_mb(),
            'total_mb': self.get_total_mb(),
            'policy_id': self.policy_id,
            'cap_upload_mbps': self.cap_upload_mbps,
            'cap_download_mbps': self.cap_download_mbps,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'is_cap_exceeded': self.is_cap_exceeded,
            'usage_percent': self.get_usage_percent(),
        }

    def __repr__(self):
        return f'<BandwidthUsage user_id={self.user_id} total={self.total_bytes}>'


class NetworkLog(db.Model):
    __tablename__ = 'network_logs'

    id = db.Column(db.Integer, primary_key=True)
    ap_id = db.Column(db.Integer, db.ForeignKey('access_points.id'), nullable=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=True)
    event_type = db.Column(
        db.Enum('auth_success', 'auth_fail', 'association', 'disassociation',
                'roaming', 'dhcp', 'ap_offline', 'ap_recovered', 'bandwidth_exceeded',
                'rogue_ap_detected', 'throttle_applied'),
        nullable=False
    )
    description = db.Column(db.Text)
    severity = db.Column(db.Enum('info', 'warning', 'critical'), default='info', nullable=False)
    ip_address = db.Column(db.String(15))
    mac_address = db.Column(db.String(17))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'ap_id': self.ap_id,
            'device_id': self.device_id,
            'event_type': self.event_type,
            'description': self.description,
            'severity': self.severity,
            'ip_address': self.ip_address,
            'mac_address': self.mac_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f'<NetworkLog {self.event_type} @ {self.timestamp}>'


class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    ap_id = db.Column(db.Integer, db.ForeignKey('access_points.id'), nullable=True)
    alert_type = db.Column(
        db.Enum('ap_offline', 'rogue_ap', 'bandwidth_exceeded', 'high_utilization',
                'auth_failure_flood', 'interference', 'ap_recovered', 'bandwidth_warning'),
        nullable=False
    )
    severity = db.Column(db.Enum('low', 'medium', 'high', 'critical'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    acknowledged_at = db.Column(db.DateTime)

    def get_severity_color(self):
        colors = {
            'low': 'secondary',
            'medium': 'warning',
            'high': 'orange',
            'critical': 'danger',
        }
        return colors.get(self.severity, 'secondary')

    def get_severity_badge(self):
        badges = {
            'low': 'bg-secondary',
            'medium': 'bg-warning text-dark',
            'high': 'bg-orange text-white',
            'critical': 'bg-danger',
        }
        return badges.get(self.severity, 'bg-secondary')

    def to_dict(self):
        return {
            'id': self.id,
            'ap_id': self.ap_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'severity_color': self.get_severity_color(),
            'message': self.message,
            'is_acknowledged': self.is_acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }

    def __repr__(self):
        return f'<Alert {self.alert_type} ({self.severity})>'


class RogueAP(db.Model):
    __tablename__ = 'rogue_aps'

    id = db.Column(db.Integer, primary_key=True)
    mac_address = db.Column(db.String(17), nullable=False, index=True)
    ssid = db.Column(db.String(100))
    signal_strength = db.Column(db.Integer)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    detected_by_ap_id = db.Column(db.Integer, db.ForeignKey('access_points.id'), nullable=True)
    status = db.Column(db.Enum('pending', 'confirmed', 'dismissed'), default='pending')
    channel = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'mac_address': self.mac_address,
            'ssid': self.ssid,
            'signal_strength': self.signal_strength,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'detected_by_ap_id': self.detected_by_ap_id,
            'status': self.status,
            'channel': self.channel,
        }

    def __repr__(self):
        return f'<RogueAP {self.mac_address} ({self.status})>'
