"""
Algorithm 3: Bandwidth Policy Enforcement.
Runs every BANDWIDTH_CHECK_INTERVAL seconds (120s default).
Checks all active bandwidth_usage records against their assigned policy caps.
"""
import random
import logging
from datetime import datetime, timedelta
from app.models import db, BandwidthUsage, BandwidthPolicy, Alert, NetworkLog, User

logger = logging.getLogger(__name__)


class BandwidthEnforcer:
    def __init__(self, app):
        self.app = app

    def enforce_policies(self):
        """Algorithm 3: Enforce per-user bandwidth caps."""
        with self.app.app_context():
            now = datetime.utcnow()
            # Simulate new traffic for active sessions (random increment)
            records = BandwidthUsage.query.filter(
                BandwidthUsage.period_end >= now
            ).all()

            for record in records:
                self._simulate_traffic(record)
                self._check_cap(record, now)

            # Reset daily counters for expired periods
            expired = BandwidthUsage.query.filter(BandwidthUsage.period_end < now).all()
            for record in expired:
                record.period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                record.period_end = record.period_start + timedelta(days=1)
                record.upload_bytes = 0
                record.download_bytes = 0
                record.total_bytes = 0
                record.is_cap_exceeded = False

            try:
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                logger.error('Bandwidth enforcer commit error: %s', exc)

    def _simulate_traffic(self, record):
        """Simulate incremental traffic per enforcement cycle."""
        upload_inc = random.randint(1_000_000, 50_000_000)    # 1–50 MB
        download_inc = random.randint(5_000_000, 200_000_000) # 5–200 MB
        record.upload_bytes += upload_inc
        record.download_bytes += download_inc
        record.total_bytes = record.upload_bytes + record.download_bytes

    def _check_cap(self, record, now):
        if not record.cap_download_mbps:
            return
        # Cap in bytes for a 24-hour period
        cap_bytes = record.cap_download_mbps * 1024 * 1024 * 3600 * 8
        usage_ratio = record.download_bytes / cap_bytes if cap_bytes > 0 else 0

        if usage_ratio >= 1.0 and not record.is_cap_exceeded:
            record.is_cap_exceeded = True
            msg = (f'User ID {record.user_id} exceeded download cap of '
                   f'{record.cap_download_mbps} Mbps '
                   f'(used {record.download_bytes / (1024**3):.2f} GB)')
            alert = Alert(alert_type='bandwidth_exceeded', severity='high',
                          message=msg, is_acknowledged=False)
            db.session.add(alert)
            log = NetworkLog(event_type='bandwidth_exceeded', description=msg,
                             severity='warning', timestamp=now)
            db.session.add(log)
            logger.info('Throttle applied: %s', msg)
        elif usage_ratio >= 0.9 and not record.is_cap_exceeded:
            # Warning at 90%
            existing = Alert.query.filter_by(alert_type='bandwidth_warning',
                                              is_acknowledged=False).filter(
                Alert.message.like(f'%User ID {record.user_id}%')).first()
            if not existing:
                msg = (f'User ID {record.user_id} is at {usage_ratio*100:.1f}% '
                       f'of download cap ({record.cap_download_mbps} Mbps)')
                alert = Alert(alert_type='bandwidth_warning', severity='medium',
                              message=msg, is_acknowledged=False)
                db.session.add(alert)
