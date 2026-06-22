from flask import Blueprint

access_points_bp = Blueprint('access_points', __name__, template_folder='../templates/access_points')

from . import routes  # noqa: F401, E402
