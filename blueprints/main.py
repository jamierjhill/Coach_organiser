# blueprints/main.py
from flask import Blueprint, render_template, redirect, request, session
from flask_login import login_required, current_user
import os

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def root():
    return redirect("/login")

@main_bp.route("/home")
@login_required
def home():
    return render_template("home.html")

@main_bp.route("/guide")
def guide():
    return render_template("coach_guide.html")

@main_bp.route("/contact")
def contact():
    return render_template("contact.html")

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

