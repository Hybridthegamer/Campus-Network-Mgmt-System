"""
Simulated SNMP Service — implements Algorithm 1 polling loop.
In production this would issue real SNMPv3 GetRequests against AP MIBs.
"""
import random
import logging
from datetime import datetime
from app.models import db, AccessPoint, NetworkLog, Alert

logger = logging.getLogger(__name__)


class SimulatedSNMPService:
    def __init__(self, app):
        self.app = app

    def poll_all_aps(self):
        """Poll every registered AP (simulated). Runs every SNMP_POLL_INTERVAL seconds."""
        with self.app.app_context():
            aps = AccessPoint.query.all()
            for ap in aps:
                self._poll_ap(ap)
            try:
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                logger.error('SNMP poll commit failed: %s', exc)

    def _poll_ap(self, ap):
        now = datetime.utcnow()
        # Simulate 90% uptime — 10% chance AP goes offline per poll cycle
        was_online = ap.status == 'online'
        goes_offline = random.random() < 0.05
        comes_online = random.random() < 0.8

        if ap.status == 'offline' and comes_online:
            ap.status = 'online'
            self._log_event(ap, 'ap_recovered', 'AP came back online', 'info')
            self._create_alert(ap, 'ap_recovered', 'low', f'{ap.ap_name} recovered and is back online.')
        elif ap.status == 'online' and goes_offline:
            ap.status = 'offline'
            self._log_event(ap, 'ap_offline', f'AP {ap.ap_name} went offline (no SNMP response)', 'critical')
            self._create_alert(ap, 'ap_offline', 'critical', f'{ap.ap_name} is offline — no SNMP response.')
        else:
            # Update simulated metrics
            ap.client_count = random.randint(0, 48)
            ap.channel_utilization = round(random.uniform(10.0, 85.0), 1)
            ap.uptime_seconds = (ap.uptime_seconds or 0) + 60
            ap.tx_power = ap.tx_power or random.choice([17, 20, 23])
            ap.channel_24ghz = ap.channel_24ghz or random.choice([1, 6, 11])
            ap.channel_5ghz = ap.channel_5ghz or random.choice([36, 40, 44, 48, 149, 153, 157, 161])
            if ap.channel_utilization > 80:
                ap.status = 'degraded'
                self._create_alert(ap, 'high_utilization', 'high',
                                   f'{ap.ap_name} channel utilization at {ap.channel_utilization:.1f}%')
            else:
                ap.status = 'online'

        ap.last_polled = now

    def _log_event(self, ap, event_type, description, severity):
        log = NetworkLog(ap_id=ap.id, event_type=event_type,
                         description=description, severity=severity,
                         timestamp=datetime.utcnow())
        db.session.add(log)

    def _create_alert(self, ap, alert_type, severity, message):
        existing = Alert.query.filter_by(ap_id=ap.id, alert_type=alert_type,
                                         is_acknowledged=False).first()
        if not existing:
            alert = Alert(ap_id=ap.id, alert_type=alert_type, severity=severity,
                          message=message, is_acknowledged=False)
            db.session.add(alert)
