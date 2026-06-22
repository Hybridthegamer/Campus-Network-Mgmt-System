"""Alert helper functions for creating and sending alerts."""
import logging
from datetime import datetime
from app.models import db, Alert

logger = logging.getLogger(__name__)


def create_alert(alert_type, severity, message, ap_id=None):
    """Create an alert record, avoiding duplicate unacknowledged alerts."""
    existing = Alert.query.filter_by(alert_type=alert_type, ap_id=ap_id,
                                      is_acknowledged=False).first()
    if existing:
        return existing
    alert = Alert(alert_type=alert_type, severity=severity, message=message,
                  ap_id=ap_id, is_acknowledged=False)
    db.session.add(alert)
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error('Failed to create alert: %s', exc)
        return None
    return alert


def acknowledge_alert(alert_id, user_id):
    alert = Alert.query.get(alert_id)
    if alert:
        alert.is_acknowledged = True
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()
        db.session.commit()
    return alert
