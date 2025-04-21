from flask import Blueprint, render_template, request, redirect, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User, load_users, save_users

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
        password = request.form.get("password")

        users = load_users()
        if username in users:
            return render_template("register.html", error="Username already exists.")

        users[username] = password
        save_users(users)

        user = User(id=username, username=username)
        login_user(user)
        return redirect("/home")

    return render_template("register.html")

