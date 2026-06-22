from flask import Blueprint

alerts_bp = Blueprint('alerts', __name__, template_folder='../templates/alerts')

from . import routes  # noqa: F401, E402
