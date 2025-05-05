# Import optimization to prevent circular imports
import os
import json
from functools import lru_cache
from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from utils import get_weather
from user_utils import load_user
from pathlib import Path

player_bp = Blueprint("player", __name__)

SESSION_CODE_FILE = "data/session_codes.json"
EMAILS_DIR = "data/emails"
BULLETINS_DIR = "data/bulletins"

@lru_cache(maxsize=1)
def load_codes():
    """
    Load access codes with caching to improve performance.
    
    Returns:
        dict: Dictionary of access codes
    """
    code_path = Path(SESSION_CODE_FILE)
    if code_path.exists():
        try:
            with open(code_path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"❌ Error parsing session codes file")
        except Exception as e:
            print(f"❌ Error loading session codes: {e}")
    return {}

@player_bp.route("/player-access", methods=["GET", "POST"])
def player_access():
    if request.method == "POST":
        code = request.form.get("access_code", "").strip().upper()
        codes = load_codes()
        
        if not code:
            flash("❌ Please enter an access code.", "danger")
            return redirect(url_for("auth.login"))
            
        if code in codes:
            session["player_code"] = code
            email = request.args.get("email", "").strip().lower()
            if email:
                session["subscriber_email"] = email
            return redirect(url_for("player.player_portal"))
            
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

    # Load coach's bulletin
    bulletin_path = os.path.join(BULLETINS_DIR, f"{coach}.json")
    bulletin_messages = []
    if os.path.exists(bulletin_path):
        with open(bulletin_path) as f:
            bulletin_messages = json.load(f)

    # Load coach's postcode and weather
    coach_data = load_user(coach)
    postcode = coach_data.get("default_postcode", "SW6 4UL") if coach_data else "SW6 4UL"
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

    os.makedirs(EMAILS_DIR, exist_ok=True)
    filepath = os.path.join(EMAILS_DIR, f"{coach}.json")

    emails = set()
    if os.path.exists(filepath):
        with open(filepath) as f:
            emails = set(json.load(f))

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

    filepath = os.path.join(EMAILS_DIR, f"{coach}.json")

    if os.path.exists(filepath):
        with open(filepath) as f:
            emails = set(json.load(f))
        emails.discard(email)
        with open(filepath, "w") as f:
            json.dump(list(emails), f, indent=2)

    flash("✅ You've been unsubscribed from coach updates.", "info")
    return redirect(url_for("player.player_portal"))
