import logging
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .models import db, User
from config import config

login_manager = LoginManager()
mail = Mail()
scheduler = BackgroundScheduler(daemon=True)


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .access_points import access_points_bp
    from .users_mgmt import users_mgmt_bp
    from .monitoring import monitoring_bp
    from .alerts import alerts_bp
    from .reports import reports_bp
    from .bandwidth import bandwidth_bp
    from .api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(access_points_bp, url_prefix='/access-points')
    app.register_blueprint(users_mgmt_bp, url_prefix='/users')
    app.register_blueprint(monitoring_bp, url_prefix='/monitoring')
    app.register_blueprint(alerts_bp, url_prefix='/alerts')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(bandwidth_bp, url_prefix='/bandwidth')
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    # Start background scheduler
    _start_scheduler(app)

    return app


def _start_scheduler(app):
    """Start APScheduler with background jobs."""
    if scheduler.running:
        return

    from .services.snmp_service import SimulatedSNMPService
    from .services.rogue_ap_detector import RogueAPDetector
    from .services.bandwidth_enforcer import BandwidthEnforcer

    snmp_svc = SimulatedSNMPService(app)
    rogue_detector = RogueAPDetector(app)
    bw_enforcer = BandwidthEnforcer(app)

    poll_interval = app.config.get('SNMP_POLL_INTERVAL', 60)
    rogue_interval = app.config.get('ROGUE_AP_SCAN_INTERVAL', 300)
    bw_interval = app.config.get('BANDWIDTH_CHECK_INTERVAL', 120)

    scheduler.add_job(
        func=snmp_svc.poll_all_aps,
        trigger=IntervalTrigger(seconds=poll_interval),
        id='snmp_poll',
        name='SNMP AP Poll',
        replace_existing=True,
    )
    scheduler.add_job(
        func=rogue_detector.run_detection,
        trigger=IntervalTrigger(seconds=rogue_interval),
        id='rogue_ap_detect',
        name='Rogue AP Detection',
        replace_existing=True,
    )
    scheduler.add_job(
        func=bw_enforcer.enforce_policies,
        trigger=IntervalTrigger(seconds=bw_interval),
        id='bandwidth_enforce',
        name='Bandwidth Policy Enforcement',
        replace_existing=True,
    )

    try:
        scheduler.start()
        logging.getLogger(__name__).info('APScheduler started successfully.')
    except Exception as exc:
        logging.getLogger(__name__).warning(f'APScheduler failed to start: {exc}')
