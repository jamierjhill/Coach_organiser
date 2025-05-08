import os
import json
import random
import string
from uuid import uuid4
from datetime import datetime
from flask import Blueprint, render_template, redirect, request, session, flash
from flask_login import login_required, current_user
from user_utils import load_user
from utils import get_weather

main_bp = Blueprint("main", __name__)

# === BULLETINS ===
def load_bulletin():
    coach = current_user.username
    filepath = f"data/bulletins/{coach}.json"
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

@main_bp.route("/")
def root():
    if current_user.is_authenticated:
        return redirect("/home")
    return redirect("/login")

@main_bp.route("/home")
@login_required
def home():
    try:
        user_data = load_user(current_user.username)
        postcode = user_data.get("default_postcode", "SW6 4UL") if user_data else "SW6 4UL"
        bulletin_messages = load_bulletin()
        
        # Initialize match organizer variables with defaults
        players = session.get("players", [])
        courts = session.get("courts", 1)
        num_matches = session.get("num_matches", 1)
        match_type = session.get("match_type", "singles")
        session_name = session.get("session_name", "")
        view_mode = session.get("view_mode", "court")
        matchups = session.get("matchups", [])
        player_match_counts = session.get("player_match_counts", {})
        opponent_averages = session.get("opponent_averages", {})
        opponent_diff = session.get("opponent_diff", {})
        rounds = session.get("rounds", {})
        
        return render_template(
            "home.html", 
            default_postcode=postcode, 
            bulletin_messages=bulletin_messages,
            players=players,
            courts=courts,
            num_matches=num_matches,
            match_type=match_type,
            matchups=matchups,
            player_match_counts=player_match_counts,
            session_name=session_name,
            opponent_averages=opponent_averages,
            opponent_diff=opponent_diff,
            rounds=rounds,
            view_mode=view_mode
        )
    except Exception as e:
        # FIXED: Instead of redirecting to login, log the error and return a simpler home page
        print(f"Error loading home page details: {e}")
        return render_template(
            "home.html", 
            default_postcode="SW6 4UL", 
            bulletin_messages=[],
            error=f"Some data couldn't be loaded. Please refresh or contact support if the issue persists."
        )

@main_bp.route("/bulletin")
@login_required
def bulletin():
    messages = load_bulletin()
    return render_template("bulletin.html", bulletin_messages=messages)

@main_bp.route("/post-bulletin", methods=["POST"])
@login_required
def post_bulletin():
    session["last_form_page"] = "/bulletin"
    message = request.form.get("message", "").strip()
    send_email = "send_email" in request.form
    if not message:
        return '', 204

    coach = current_user.username
    filepath = f"data/bulletins/{coach}.json"
    os.makedirs("data/bulletins", exist_ok=True)
    messages = []
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            messages = json.load(f)

    messages.append({
        "id": str(uuid4()),
        "text": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    with open(filepath, "w") as f:
        json.dump(messages, f, indent=2)

    if send_email:
        send_bulletin_emails(coach, message)

    return '', 204

def send_bulletin_emails(coach, text):
    from app import mail
    from flask_mail import Message

    filepath = f"data/emails/{coach}.json"
    if not os.path.exists(filepath):
        return

    with open(filepath) as f:
        emails = json.load(f)

    subject = f"🎾 New Bulletin from Coach {coach.capitalize()}"

    for email in emails:
        body = (
            f"Hi there,\n\nCoach {coach.capitalize()} has posted a new bulletin:\n\n"
            f"{text}\n\n"
            f"If you no longer want to receive updates, you can unsubscribe in the player portal\n\n"
            f"— Coaches Hub"
        )
        try:
            msg = Message(subject=subject, recipients=[email], body=body)
            mail.send(msg)
        except Exception as e:
            print(f"❌ Failed to send to {email}: {e}")

@main_bp.route("/delete-bulletin/<msg_id>", methods=["POST"])
@login_required
def delete_bulletin(msg_id):
    coach = current_user.username
    filepath = f"data/bulletins/{coach}.json"
    if not os.path.exists(filepath):
        return redirect("/bulletin")

    with open(filepath, "r") as f:
        messages = json.load(f)
    messages = [msg for msg in messages if msg.get("id") != msg_id]

    with open(filepath, "w") as f:
        json.dump(messages, f, indent=2)

    return redirect("/bulletin")

@main_bp.route("/guide")
def guide():
    return render_template("coach_guide.html")

# === NOTES ===
@main_bp.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    session["last_form_page"] = "/notes"
    username = current_user.username
    notes_path = f"notes/{username}.json"
    os.makedirs("notes", exist_ok=True)

    notes_list = []
    if os.path.exists(notes_path):
        with open(notes_path, "r") as f:
            notes_list = json.load(f)

    if request.method == "POST":
        if "note" in request.form:
            new_note = request.form["note"].strip()
            if new_note:
                notes_list.append(new_note)
        elif "delete_note" in request.form:
            to_delete = request.form["delete_note"].strip()
            notes_list = [n for n in notes_list if n != to_delete]

        with open(notes_path, "w") as f:
            json.dump(notes_list, f, indent=2)

        return '', 204

    return render_template("notes.html", notes=notes_list)

# === CONTACT ===
@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    session["last_form_page"] = "/contact"

    if request.method == "POST":
        from app import mail
        from flask_mail import Message

        name = request.form.get("name")
        email = request.form.get("email")
        message_body = request.form.get("message")

        msg = Message(
            subject=f"📩 Contact Form from {name}",
            sender=email,
            recipients=["coacheshubteam@gmail.com"],
            body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message_body}"
        )

        try:
            mail.send(msg)
            flash("✅ Message sent successfully!", "success")
        except Exception:
            flash("⚠️ Failed to send message. Please try again later.", "danger")

        return redirect("/home" if "go_home" in request.form else "/contact")

    return render_template("contact.html")

# === WEATHER ===
@main_bp.route("/weather")
@login_required
def weather():
    user_data = load_user(current_user.username)
    postcode = user_data.get("default_postcode", "SW6 4UL") if user_data else "SW6 4UL"
    weather = get_weather(postcode)
    return render_template("weather.html", weather=weather, default_postcode=postcode)

# === ACCESS CODES ===
@main_bp.route("/access-codes", methods=["GET", "POST"])
@login_required
def access_codes():
    session["last_form_page"] = "/access-codes"
    filepath = "data/session_codes.json"

    codes = {}
    if os.path.exists(filepath):
        with open(filepath) as f:
            codes = json.load(f)

    coach = current_user.username

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if "go_home" in request.form:
            return redirect("/home")
        if not title:
            return '', 400

        new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        codes[new_code] = {
            "title": title,
            "created_by": coach
        }

        with open(filepath, "w") as f:
            json.dump(codes, f, indent=2)
        flash(f"✅ Created code: {new_code}", "success")
        return '', 204

    coach_codes = {code: data for code, data in codes.items() if data["created_by"] == coach}
    return render_template("access_codes.html", codes=coach_codes)

@main_bp.route("/delete-access-code/<code>", methods=["POST"])
@login_required
def delete_access_code(code):
    filepath = "data/session_codes.json"
    if not os.path.exists(filepath):
        return '', 404

    with open(filepath) as f:
        codes = json.load(f)

    if code in codes and codes[code].get("created_by") == current_user.username:
        del codes[code]
        with open(filepath, "w") as f:
            json.dump(codes, f, indent=2)
        return '', 204
    return '', 403