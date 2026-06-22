"""
Algorithm 2: Rogue Access Point Detection.
Runs every ROGUE_AP_SCAN_INTERVAL seconds (300s default).
Simulates scanning neighbor APs via SNMP dot11StationConfigEntry MIB.
"""
import random
import logging
from datetime import datetime
from app.models import db, AccessPoint, RogueAP, Alert, NetworkLog

logger = logging.getLogger(__name__)

_FAKE_SSIDS = ['FreeWiFi', 'CampusGuest', 'AndroidAP', 'iPhone_HotSpot',
               'DIRECT-xx-HP', 'linksys', 'NETGEAR_5G', 'xfinitywifi']


def _random_mac():
    return ':'.join(f'{random.randint(0, 255):02X}' for _ in range(6))


class RogueAPDetector:
    def __init__(self, app):
        self.app = app

    def run_detection(self):
        """Algorithm 2: Compare detected MACs against authorized AP list."""
        with self.app.app_context():
            authorized_macs = {ap.mac_address.upper()
                               for ap in AccessPoint.query.all()}
            online_aps = AccessPoint.query.filter_by(status='online').all()

            for detecting_ap in online_aps:
                # Simulate: 15% chance of detecting a rogue AP per online AP per scan
                if random.random() < 0.15:
                    rogue_mac = _random_mac()
                    if rogue_mac.upper() not in authorized_macs:
                        self._handle_rogue(rogue_mac, detecting_ap)

            try:
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                logger.error('Rogue AP detector commit error: %s', exc)

    def _handle_rogue(self, mac, detecting_ap):
        signal = random.randint(-80, -30)
        channel = random.choice([1, 6, 11, 36, 40, 44, 149])
        ssid = random.choice(_FAKE_SSIDS)
        now = datetime.utcnow()

        existing = RogueAP.query.filter_by(mac_address=mac, status='confirmed').first()
        if existing:
            existing.detected_at = now
            return

        pending = RogueAP.query.filter_by(mac_address=mac, status='pending').first()
        if not pending:
            rogue = RogueAP(mac_address=mac, ssid=ssid, signal_strength=signal,
                            detected_at=now, detected_by_ap_id=detecting_ap.id,
                            status='pending', channel=channel)
            db.session.add(rogue)

            severity = 'critical' if signal > -50 else 'high'
            alert_msg = (f'Rogue AP detected: MAC {mac}, SSID "{ssid}", '
                         f'Signal {signal} dBm, Channel {channel}, '
                         f'detected by {detecting_ap.ap_name}')
            existing_alert = Alert.query.filter_by(alert_type='rogue_ap',
                                                    is_acknowledged=False).filter(
                Alert.message.like(f'%{mac}%')).first()
            if not existing_alert:
                alert = Alert(ap_id=detecting_ap.id, alert_type='rogue_ap',
                              severity=severity, message=alert_msg,
                              is_acknowledged=False)
                db.session.add(alert)

            log = NetworkLog(ap_id=detecting_ap.id, event_type='rogue_ap_detected',
                             description=alert_msg, severity='critical',
                             mac_address=mac, timestamp=now)
            db.session.add(log)
            logger.warning('Rogue AP detected: %s via %s', mac, detecting_ap.ap_name)
