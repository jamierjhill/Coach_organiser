from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_required, current_user
import os, json

settings_bp = Blueprint("settings", __name__)

SETTINGS_FILE = "data/user_settings.json"

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = current_user.username
    settings = load_settings()

    if request.method == "POST":
        postcode = request.form.get("postcode", "").strip()
        settings[user] = {"default_postcode": postcode}
        save_settings(settings)
        flash("Settings saved!", "success")
        return redirect("/settings")

    user_settings = settings.get(user, {})
    return render_template("settings.html", user_settings=user_settings)
