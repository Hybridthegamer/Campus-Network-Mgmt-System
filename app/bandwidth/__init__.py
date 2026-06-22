from flask import Blueprint

bandwidth_bp = Blueprint('bandwidth', __name__, template_folder='../templates/bandwidth')

from . import routes  # noqa: F401, E402
