from flask import Blueprint

users_mgmt_bp = Blueprint('users_mgmt', __name__, template_folder='../templates/users_mgmt')

from . import routes  # noqa: F401, E402
