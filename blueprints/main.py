import os
import json
from flask import Blueprint, render_template, redirect, request, session, flash
from flask_login import login_required, current_user
from blueprints.settings import load_settings
from datetime import datetime
from uuid import uuid4
import random
import string

main_bp = Blueprint("main", __name__)

# ✅ Utility: Load coach-specific bulletin file
def load_bulletin():
    coach = current_user.username
    filepath = f"data/bulletins/{coach}.json"
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

@main_bp.route("/")
def root():
    return redirect("/login")


@main_bp.route("/home")
@login_required
def home():
    settings = load_settings()
    postcode = settings.get(current_user.username, {}).get("default_postcode", "SW6 4UL")
    bulletin_messages = load_bulletin()
    return render_template("home.html", default_postcode=postcode, bulletin_messages=bulletin_messages)


@main_bp.route("/bulletin")
@login_required
def bulletin():
    messages = load_bulletin()
    return render_template("bulletin.html", bulletin_messages=messages)


@main_bp.route("/post-bulletin", methods=["POST"])
@login_required
def post_bulletin():
    from app import mail
    from flask_mail import Message

    message = request.form.get("message", "").strip()
    send_email = "send_email" in request.form  # ✅ Check checkbox state

    if not message:
        return redirect("/bulletin")

    coach = current_user.username
    filepath = f"data/bulletins/{coach}.json"
    os.makedirs("data/bulletins", exist_ok=True)

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            messages = json.load(f)
    else:
        messages = []

    new_msg = {
        "id": str(uuid4()),
        "text": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    messages.append(new_msg)

    with open(filepath, "w") as f:
        json.dump(messages, f, indent=2)

    # ✅ Only send email if box was ticked
    if send_email:
        send_bulletin_emails(coach, message)

    return redirect("/bulletin")



def send_bulletin_emails(coach, text):
    from app import mail
    from flask_mail import Message

    filepath = f"data/emails/{coach}.json"
    if not os.path.exists(filepath):
        return

    with open(filepath) as f:
        emails = json.load(f)

    subject = f"🎾 New Bulletin from Coach {coach.capitalize()}"

    base_url = os.getenv("APP_BASE_URL", "http://localhost:5000")

    for email in emails:
        body = (
            f"Hi there,\n\n"
            f"Coach {coach.capitalize()} has posted a new bulletin:\n\n"
            f"{text}\n\n"
            f"If you no longer want to receive updates, you can unsubscribe here in the player portal"
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


@main_bp.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    notes_file = f"notes/{current_user.username}.txt"
    os.makedirs("notes", exist_ok=True)

    if request.method == "POST":
        if "note" in request.form:
            note = request.form["note"].strip()
            if note:
                with open(notes_file, "a") as f:
                    f.write(note + "\n")
        elif "delete_note" in request.form:
            to_delete = request.form["delete_note"].strip()
            if os.path.exists(notes_file):
                with open(notes_file, "r") as f:
                    notes = f.readlines()
                notes = [n for n in notes if n.strip() != to_delete]
                with open(notes_file, "w") as f:
                    f.writelines(notes)
        return redirect("/notes")

    notes_list = []
    if os.path.exists(notes_file):
        with open(notes_file, "r") as f:
            notes_list = [line.strip() for line in f.readlines()]

    return render_template("notes.html", notes=notes_list)


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
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

        return redirect("/contact")

    return render_template("contact.html")


from utils import get_weather

@main_bp.route("/weather")
@login_required
def weather():
    settings = load_settings()
    postcode = settings.get(current_user.username, {}).get("default_postcode", "SW6 4UL")
    weather = get_weather(postcode)
    return render_template("weather.html", weather=weather, default_postcode=postcode)


@main_bp.route("/access-codes", methods=["GET", "POST"])
@login_required
def access_codes():
    filepath = "data/session_codes.json"
    if os.path.exists(filepath):
        with open(filepath) as f:
            codes = json.load(f)
    else:
        codes = {}

    coach = current_user.username

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if title:
            new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            codes[new_code] = {
                "title": title,
                "created_by": coach
            }
            with open(filepath, "w") as f:
                json.dump(codes, f, indent=2)
            flash(f"✅ Created code: {new_code}", "success")
        return redirect("/access-codes")

    coach_codes = {code: data for code, data in codes.items() if data["created_by"] == coach}
    return render_template("access_codes.html", codes=coach_codes)


@main_bp.route("/delete-access-code/<code>", methods=["POST"])
@login_required
def delete_access_code(code):
    filepath = "data/session_codes.json"
    if not os.path.exists(filepath):
        return redirect("/access-codes")

    with open(filepath) as f:
        codes = json.load(f)

    if code in codes and codes[code].get("created_by") == current_user.username:
        del codes[code]
        with open(filepath, "w") as f:
            json.dump(codes, f, indent=2)
        flash(f"🗑️ Deleted access code: {code}", "success")
    else:
        flash("⚠️ You are not authorized to delete this code.", "danger")

    return redirect("/access-codes")
