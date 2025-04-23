from flask import Blueprint, render_template, request, redirect, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User, load_users, save_users
from blueprints.settings import load_settings, save_settings  # Add this import if not present
from flask import current_app
from flask_mail import Message


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        users = load_users()
        if username in users and users[username] == password:
            user = User(id=username, username=username)
            login_user(user)
            return redirect("/home")

        return render_template("login.html", error="Invalid credentials.")
    return render_template("login.html")




@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/login?message=You’ve been logged out successfully.")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        postcode = request.form.get("postcode", "").strip()
        password = request.form.get("password")

        users = load_users()
        if username in users:
            return render_template("register.html", error="Username already exists.")

        users[username] = password
        save_users(users)

        # Save postcode to settings
        from blueprints.settings import load_settings, save_settings
        settings = load_settings()
        settings[username] = {"default_postcode": postcode}
        save_settings(settings)

        user = User(id=username, username=username)
        login_user(user)

        # ✉️ Send welcome email
        try:
            from flask_mail import Message
            from flask import current_app
            mail = current_app.extensions["mail"]
            msg = Message(
                subject="🎾 Welcome to Coaches Hub!",
                recipients=[email],
                body=(
                    f"Hi {username},\n\n"
                    "Welcome to Coaches Hub! 🏆\n"
                    "You can now organize matches, plan sessions, check forecasts, and more.\n\n"
                    "Explore your dashboard and start coaching smarter today!\n\n"
                    "– The Coaches Hub Team"
                )
            )
            mail.send(msg)
        except Exception as e:
            print("⚠️ Email sending failed:", e)

        return redirect("/home")

    return render_template("register.html")





