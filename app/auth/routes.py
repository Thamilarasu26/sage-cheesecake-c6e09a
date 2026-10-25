"""
Authentication routes: register, login, logout, profile.
"""

import re
from flask import (
    render_template, redirect, url_for, flash,
    request, session, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from app import db, limiter
from app.models import User
from app.auth import auth_bp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN = 8


def _validate_password(pw: str) -> list[str]:
    errors = []
    if len(pw) < PASSWORD_MIN:
        errors.append(f"Password must be at least {PASSWORD_MIN} characters.")
    if not any(c.isupper() for c in pw):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(c.isdigit() for c in pw):
        errors.append("Password must contain at least one digit.")
    return errors


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if not name:
            errors.append("Full name is required.")
        if not EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")
        pw_errors = _validate_password(password)
        errors.extend(pw_errors)
        if password != confirm:
            errors.append("Passwords do not match.")

        if not errors:
            if User.query.filter_by(email=email).first():
                errors.append("An account with that email already exists.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html",
                                   name=name, email=email)

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            session.permanent = True
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(next_page or url_for("main.dashboard"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


# ---------------------------------------------------------------------------
# Profile / Settings
# ---------------------------------------------------------------------------
@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_name":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Name cannot be empty.", "danger")
            else:
                current_user.name = name
                db.session.commit()
                flash("Name updated successfully.", "success")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_pw = request.form.get("confirm_password", "")

            if not current_user.check_password(current_pw):
                flash("Current password is incorrect.", "danger")
            elif new_pw != confirm_pw:
                flash("New passwords do not match.", "danger")
            else:
                pw_errors = _validate_password(new_pw)
                if pw_errors:
                    for e in pw_errors:
                        flash(e, "danger")
                else:
                    current_user.set_password(new_pw)
                    db.session.commit()
                    flash("Password changed successfully.", "success")

        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html")
