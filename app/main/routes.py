"""Main (landing/redirect) routes."""

from flask import render_template, redirect, url_for
from flask_login import current_user
from app.main import main_bp


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("files.dashboard"))
    return render_template("main/index.html")


@main_bp.route("/dashboard")
def dashboard():
    return redirect(url_for("files.dashboard"))
