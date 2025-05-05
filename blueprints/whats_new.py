# Add this to a new file: blueprints/whats_new.py

from flask import Blueprint, render_template, redirect
from flask_login import login_required

whats_new_bp = Blueprint("whats_new", __name__)

@whats_new_bp.route("/whats-new")
def whats_new():
    """Display the What's New page with updates and new features."""
    return render_template("whats_new.html")