from flask import Blueprint

monitoring_bp = Blueprint('monitoring', __name__, template_folder='../templates/monitoring')

from . import routes  # noqa: F401, E402
