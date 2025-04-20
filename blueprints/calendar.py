from flask import Blueprint, render_template, jsonify, request, session, redirect
from flask_login import login_required, current_user
import os, json

calendar_bp = Blueprint("calendar", __name__)

@calendar_bp.route("/calendar")
@login_required
def calendar():
    return render_template("calendar.html")

@calendar_bp.route("/api/events", methods=["GET", "POST"])
@login_required
def events():
    coach = current_user.username
    filepath = f"data/events/events_{coach}.json"

    if request.method == "GET":
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return jsonify(json.load(f))
        return jsonify([])

    elif request.method == "POST":
        events = request.json.get("events", [])
        os.makedirs("data/events", exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(events, f)
        return jsonify({"success": True})
