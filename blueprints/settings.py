from flask import Blueprint, render_template, request, redirect, flash, session
from flask_login import login_required, current_user
import os, json
from models import load_users, save_users

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
    session["last_form_page"] = "/settings"
    settings = load_settings()

    if request.method == "POST":
        # Retrieve postcode early, apply later
        postcode = request.form.get("postcode", "").strip()

        # Handle username change
        new_username = request.form.get("new_username", "").strip()
        if new_username and new_username != user:
            users = load_users()
            if new_username in users:
                flash("⚠️ Username already taken.", "danger")
                return redirect("/settings")
            else:
                users[new_username] = users.pop(user)
                save_users(users)

                # Migrate settings and update postcode
                settings[new_username] = settings.pop(user)
                settings[new_username]["default_postcode"] = postcode
                save_settings(settings)

                # Migrate notes
                old_notes = f"notes/{user}.txt"
                new_notes = f"notes/{new_username}.txt"
                if os.path.exists(old_notes):
                    os.rename(old_notes, new_notes)

                # Migrate bulletins
                old_bulletin = f"data/bulletins/{user}.json"
                new_bulletin = f"data/bulletins/{new_username}.json"
                if os.path.exists(old_bulletin):
                    os.rename(old_bulletin, new_bulletin)

                # Migrate events
                old_events = f"data/events/events_{user}.json"
                new_events = f"data/events/events_{new_username}.json"
                if os.path.exists(old_events):
                    os.rename(old_events, new_events)

                # Migrate emails
                old_emails = f"data/emails/{user}.json"
                new_emails = f"data/emails/{new_username}.json"
                if os.path.exists(old_emails):
                    os.rename(old_emails, new_emails)

                # Update session codes
                session_code_file = "data/session_codes.json"
                if os.path.exists(session_code_file):
                    with open(session_code_file, "r") as f:
                        session_codes = json.load(f)
                    for code, data in session_codes.items():
                        if data.get("created_by") == user:
                            data["created_by"] = new_username
                    with open(session_code_file, "w") as f:
                        json.dump(session_codes, f, indent=2)

                flash("✅ Username changed. Please log in again.", "success")
                return redirect("/logout")

        # No username change: update postcode under current user
        settings[user] = {"default_postcode": postcode}
        save_settings(settings)

        if "go_home" in request.form:
            flash("✅ Settings saved!", "success")
            return redirect("/home")

        flash("✅ Settings saved!", "success")
        return redirect("/settings")

    user_settings = settings.get(user, {})
    return render_template("settings.html", user_settings=user_settings)
