# auth.py - Enhanced with CAPTCHA functionality
import os, json
import secrets  # Add missing import
import random  # For CAPTCHA generation
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, session, current_app, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from models import User
from user_utils import load_user, save_user, delete_user_file, delete_feature_file
from user_utils import feature_path
from password_utils import hash_password, verify_password

auth_bp = Blueprint("auth", __name__)

# CAPTCHA utility functions
def generate_captcha():
    """Generate a simple math CAPTCHA question and answer."""
    # Generate two random numbers between 1-20 for addition
    # Or 1-10 for multiplication to keep numbers manageable
    operation_type = random.choice(['add', 'multiply', 'subtract'])
    
    if operation_type == 'add':
        num1 = random.randint(1, 50)
        num2 = random.randint(1, 50)
        answer = num1 + num2
        question = f"{num1} + {num2}"
    elif operation_type == 'multiply':
        num1 = random.randint(1, 12)
        num2 = random.randint(1, 12)
        answer = num1 * num2
        question = f"{num1} × {num2}"
    else:  # subtract
        num1 = random.randint(10, 50)
        num2 = random.randint(1, num1 - 1)  # Ensure positive result
        answer = num1 - num2
        question = f"{num1} - {num2}"
    
    return question, answer

def validate_captcha(user_answer, session_answer):
    """Validate the CAPTCHA answer."""
    try:
        return int(user_answer) == int(session_answer)
    except (ValueError, TypeError):
        return False

# === LOGIN ===
# Improved password validation with constant-time comparison
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Add error checking for empty fields
        if not username or not password:
            return render_template("login.html", error="Username and password are required.")

        # Add debugging for user loading
        print(f"Attempting to load user: {username}")
        user_data = load_user(username)
        if not user_data:
            print(f"User not found: {username}")
            return render_template("login.html", error="Invalid credentials.")
            
        # Check if password uses the new hashing method
        is_valid = False
        try:
            if "password_hash" in user_data:
                # Verify using hashed password
                is_valid = verify_password(
                    user_data["password_hash"], 
                    user_data["password_salt"], 
                    password
                )
            else:
                # Legacy plaintext password check with constant-time comparison
                is_valid = secrets.compare_digest(user_data.get("password", ""), password)
        except Exception as e:
            print(f"Error during password verification: {e}")
            return render_template("login.html", error="An error occurred during login. Please try again.")
            
        if is_valid:
            # Add login timestamp when user successfully logs in
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_data["last_login"] = current_time
            
            # Also track login history (last 10 logins)
            if "login_history" not in user_data:
                user_data["login_history"] = []
            
            user_data["login_history"].insert(0, current_time)
            # Keep only the last 10 login records
            user_data["login_history"] = user_data["login_history"][:10]
            
            # If using legacy password, migrate to hashed
            if "password_hash" not in user_data:
                try:
                    hashed, salt = hash_password(password)
                    user_data["password_hash"] = hashed
                    user_data["password_salt"] = salt
                    # Keep the old password field for backward compatibility
                    print(f"Migrated user {username} to hashed password")
                except Exception as e:
                    print(f"Failed to migrate password: {e}")
            
            # Save updated user data
            if not save_user(user_data):
                print(f"Failed to save user data for {username}")
                return render_template("login.html", error="An error occurred during login. Please try again.")
            
            is_admin = user_data.get("is_admin", False)
            user = User(id=username, username=username, is_admin=is_admin)
            
            try:
                login_user(user)
                print(f"User {username} logged in successfully")
                return redirect("/home")
            except Exception as e:
                print(f"Login_user failed: {e}")
                return render_template("login.html", error="An error occurred during login. Please try again.")

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
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        postcode = request.form.get("postcode", "").strip()
        password = request.form.get("password", "").strip()
        captcha_answer = request.form.get("captcha_answer", "").strip()
        gdpr_consent = request.form.get("gdpr_consent")

        # Add validation for required fields
        if not username or not email or not password:
            # Regenerate CAPTCHA for security
            question, answer = generate_captcha()
            session["captcha_answer"] = answer
            return render_template("register.html", 
                                 error="Username, email, and password are required.",
                                 captcha_question=question)

        # Validate CAPTCHA
        session_answer = session.get("captcha_answer")
        if not session_answer or not validate_captcha(captcha_answer, session_answer):
            # Generate new CAPTCHA for security
            question, answer = generate_captcha()
            session["captcha_answer"] = answer
            return render_template("register.html", 
                                 error="❌ Incorrect security verification. Please try again.",
                                 captcha_question=question)

        # Validate GDPR consent
        if not gdpr_consent:
            question, answer = generate_captcha()
            session["captcha_answer"] = answer
            return render_template("register.html", 
                                 error="⚠️ You must agree to the Privacy Policy to create an account.",
                                 captcha_question=question)

        # Clear CAPTCHA from session after successful validation
        session.pop("captcha_answer", None)

        # Ensure data directory exists
        os.makedirs("data/users", exist_ok=True)

        # Prevent duplicate users
        if load_user(username):
            question, answer = generate_captcha()
            session["captcha_answer"] = answer
            return render_template("register.html", 
                                 error="❌ Username already exists. Please choose a different username.",
                                 captcha_question=question)

        # Validate email format
        if "@" not in email or "." not in email.split("@")[-1]:
            question, answer = generate_captcha()
            session["captcha_answer"] = answer
            return render_template("register.html", 
                                 error="❌ Please enter a valid email address.",
                                 captcha_question=question)

        # Validate password strength
        if len(password) < 6:
            question, answer = generate_captcha()
            session["captcha_answer"] = answer
            return render_template("register.html", 
                                 error="❌ Password must be at least 6 characters long.",
                                 captcha_question=question)

        try:
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
                "registration_date": datetime.now().strftime("%Y-%m-%d"),
                "gdpr_consent": True,
                "gdpr_consent_date": datetime.now().isoformat(),
                "registration_ip": request.remote_addr,
                "captcha_verified": True
            }
            
            if not save_user(user_data):
                question, answer = generate_captcha()
                session["captcha_answer"] = answer
                return render_template("register.html", 
                                     error="❌ Failed to create user account. Please try again.",
                                     captcha_question=question)

            # Create User object for login
            user = User(id=username, username=username, is_admin=False)
            login_user(user)
            
            print(f"User {username} registered successfully")

            # Send welcome email
            try:
                mail = current_app.extensions.get("mail")
                if mail:
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
                print(f"⚠️ Email sending failed: {e}")
                # Continue even if email fails

            return redirect("/home")
            
        except Exception as e:
            print(f"Registration error: {e}")
            question, answer = generate_captcha()
            session["captcha_answer"] = answer
            return render_template("register.html", 
                                 error=f"❌ Registration failed: {str(e)}",
                                 captcha_question=question)

    # Handle GET request - show registration form with CAPTCHA
    question, answer = generate_captcha()
    session["captcha_answer"] = answer
    return render_template("register.html", captcha_question=question)

# === CAPTCHA REFRESH ROUTE ===
@auth_bp.route("/refresh-captcha", methods=["POST"])
def refresh_captcha():
    """AJAX endpoint to refresh CAPTCHA question."""
    try:
        question, answer = generate_captcha()
        session["captcha_answer"] = answer
        return jsonify({
            "success": True,
            "question": question
        })
    except Exception as e:
        print(f"Error refreshing CAPTCHA: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to generate new question"
        }), 500

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