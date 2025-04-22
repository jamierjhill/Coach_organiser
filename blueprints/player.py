from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from blueprints.settings import load_settings
from utils import get_weather
import json
import os

player_bp = Blueprint("player", __name__)

SESSION_CODE_FILE = "data/session_codes.json"

def load_codes():
    if os.path.exists(SESSION_CODE_FILE):
        with open(SESSION_CODE_FILE) as f:
            return json.load(f)
    return {}

@player_bp.route("/player-access", methods=["GET", "POST"])
def player_access():
    if request.method == "POST":
        code = request.form.get("access_code", "").strip().upper()
        codes = load_codes()
        if code in codes:
            session["player_code"] = code
            email = request.args.get("email", "").strip().lower()
            if email:
                session["subscriber_email"] = email
            return redirect(url_for("player.player_portal"))
        else:
            flash("❌ Invalid access code. Please try again.", "danger")
    return redirect(url_for("auth.login"))


@player_bp.route("/player-portal")
def player_portal():
    code = session.get("player_code")
    codes = load_codes()

    if not code or code not in codes:
        flash("Please enter a valid code first.", "warning")
        return redirect(url_for("auth.login"))

    portal_data = codes[code]
    coach = portal_data["created_by"]

    # Load bulletin
    bulletin_path = f"data/bulletins/{coach}.json"
    bulletin_messages = []
    if os.path.exists(bulletin_path):
        with open(bulletin_path) as f:
            bulletin_messages = json.load(f)

    # Load coach's postcode and weather
    settings = load_settings()
    postcode = settings.get(coach, {}).get("default_postcode", "SW6 4UL")
    weather = get_weather(postcode)
    forecast = weather.get("forecast", [])


    return render_template(
        "player_portal.html",
        code=code,
        title=portal_data["title"],
        bulletin_messages=bulletin_messages,
        weather=weather,
        forecast=forecast
    )

@player_bp.route("/subscribe-email", methods=["POST"])
def subscribe_email():
    code = session.get("player_code")
    email = request.form.get("email", "").strip().lower()

    if not code or not email:
        flash("❌ Invalid submission.", "danger")
        return redirect(url_for("player.player_portal"))

    codes = load_codes()
    coach = codes.get(code, {}).get("created_by")
    if not coach:
        flash("⚠️ Unauthorized.", "danger")
        return redirect(url_for("auth.login"))

    os.makedirs("data/emails", exist_ok=True)
    filepath = f"data/emails/{coach}.json"

    if os.path.exists(filepath):
        with open(filepath) as f:
            emails = set(json.load(f))
    else:
        emails = set()

    emails.add(email)
    session["subscribed"] = True
    session["subscriber_email"] = email

    with open(filepath, "w") as f:
        json.dump(list(emails), f, indent=2)

    flash("✅ You've been subscribed to coach updates!", "success")
    return redirect(url_for("player.player_portal"))

@player_bp.route("/unsubscribe-email", methods=["POST"])
def unsubscribe_email():
    code = session.get("player_code")
    email = request.form.get("email", "").strip().lower()

    if not code or not email:
        flash("❌ Please enter your email to unsubscribe.", "danger")
        return redirect(url_for("player.player_portal"))

    codes = load_codes()
    coach = codes.get(code, {}).get("created_by")
    if not coach:
        flash("⚠️ Unauthorized.", "danger")
        return redirect(url_for("auth.login"))

    filepath = f"data/emails/{coach}.json"
    if os.path.exists(filepath):
        with open(filepath) as f:
            emails = set(json.load(f))
        emails.discard(email)
        with open(filepath, "w") as f:
            json.dump(list(emails), f, indent=2)

    flash("✅ You've been unsubscribed from coach updates.", "info")
    return redirect(url_for("player.player_portal"))




