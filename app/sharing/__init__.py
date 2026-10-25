# Sharing blueprint package
from flask import Blueprint

sharing_bp = Blueprint("sharing", __name__)

from app.sharing import routes  # noqa: E402, F401
