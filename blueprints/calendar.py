from flask import Blueprint, render_template, jsonify, request, session, redirect
from flask_login import login_required, current_user
import os, json

calendar_bp = Blueprint("calendar", __name__)

@calendar_bp.route("/calendar", methods=["GET", "POST"])
@login_required
def calendar():
    # Save last visited form page for smart Save & Home
    session["last_form_page"] = "/calendar"

    if request.method == "POST":
        # Save calendar event if needed
        events = request.form.get("events_json")
        if events:
            try:
                filepath = f"data/events/events_{current_user.username}.json"
                os.makedirs("data/events", exist_ok=True)
                with open(filepath, "w") as f:
                    json.dump(json.loads(events), f)
            except Exception:
                pass

        # Redirect to home if Save + Home was used
        if "go_home" in request.form:
            return redirect("/home")

    return render_template("calendar.html")

@calendar_bp.route("/api/events", methods=["GET", "POST"])
def events():
    # Coach (logged in)
    if current_user.is_authenticated:
        coach = current_user.username
    # Player (via code)
    elif "player_code" in session:
        from blueprints.player import load_codes  # lazy import to avoid circular import
        code = session["player_code"]
        codes = load_codes()
        coach = codes.get(code, {}).get("created_by")
        if not coach:
            return jsonify({"error": "Invalid code"}), 403
    else:
        return jsonify({"error": "Unauthorized"}), 401

    filepath = f"data/events/events_{coach}.json"

    if request.method == "GET":
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return jsonify(json.load(f))
        return jsonify([])

    elif request.method == "POST":
        # Only allow coaches to edit
        if not current_user.is_authenticated:
            return jsonify({"error": "Only coaches can save events."}), 403

        events = request.json.get("events", [])
        os.makedirs("data/events", exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(events, f)
        return jsonify({"success": True})
