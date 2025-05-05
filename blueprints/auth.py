import os, json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, session, current_app, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from models import User
from user_utils import load_user, save_user, delete_user_file, delete_feature_file
from user_utils import feature_path
from password_utils import hash_password, verify_password

auth_bp = Blueprint("auth", __name__)

# === LOGIN ===
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user_data = load_user(username)
        if not user_data:
            return render_template("login.html", error="Invalid credentials.")
            
        # Check if password uses the new hashing method
        if "password_hash" in user_data:
            # Verify using hashed password
            is_valid = verify_password(
                user_data["password_hash"], 
                user_data["password_salt"], 
                password
            )
            
            if is_valid:
                is_admin = user_data.get("is_admin", False)
                user = User(id=username, username=username, is_admin=is_admin)
                login_user(user)
                return redirect("/home")
        else:
            # Legacy plaintext password check
            if user_data["password"] == password:
                # Migrate to hashed password on successful login
                hashed, salt = hash_password(password)
                user_data["password_hash"] = hashed
                user_data["password_salt"] = salt
                # Keep the old password field for backward compatibility
                save_user(user_data)
                
                is_admin = user_data.get("is_admin", False)
                user = User(id=username, username=username, is_admin=is_admin)
                login_user(user)
                return redirect("/home")

        return render_template("login.html", error="Invalid credentials.")
    
    return render_template("login.html")

# === LOGOUT ===
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/login?message=You've been logged out successfully.")

# === REGISTER ===
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    session["last_form_page"] = "/register"

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        postcode = request.form.get("postcode", "").strip()
        password = request.form.get("password")

        # Prevent duplicate users
        if load_user(username):
            return render_template("register.html", error="Username already exists.")

        # Hash the password
        hashed_password, salt = hash_password(password)
        
        # Create user file with hashed password
        user_data = {
            "username": username,
            "email": email,  # Now storing email too for admin features
            "password": password,  # Keep for backward compatibility
            "password_hash": hashed_password,
            "password_salt": salt,
            "default_postcode": postcode,
            "is_admin": False,  # Default not admin
            "registration_date": datetime.now().strftime("%Y-%m-%d")
        }
        save_user(user_data)

        # Create User object for login
        user = User(id=username, username=username, is_admin=False)
        login_user(user)

        # Send welcome email
        try:
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

        return redirect("/home" if "go_home" in request.form else "/home")

    return render_template("register.html")

# === DELETE ACCOUNT ===
@auth_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    username = current_user.username

    # Remove user file
    delete_user_file(username)

    # Remove associated files
    feature_files = [
        ("notes", username, ""),               # notes/username.json
        ("data/bulletins", username, ""),      # bulletins/username.json
        ("data/events", username, ""),         # events/username.json
        ("data/emails", username, "")          # emails/username.json
    ]

    for folder, user, prefix in feature_files:
        delete_feature_file(folder, user, prefix)

    # Remove access codes created by this user
    codes_path = "data/session_codes.json"
    if os.path.exists(codes_path):
        with open(codes_path) as f:
            codes = json.load(f)
        codes = {k: v for k, v in codes.items() if v.get("created_by") != username}
        with open(codes_path, "w") as f:
            json.dump(codes, f, indent=2)

    logout_user()
    session.clear()
    return redirect("/login?message=Your account has been permanently deleted.")