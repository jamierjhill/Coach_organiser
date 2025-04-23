import os, json
from flask import Blueprint, render_template, jsonify, request, session, redirect
from flask_login import login_required, current_user

calendar_bp = Blueprint("calendar", __name__)

EVENTS_DIR = "data/events"

def get_events_path(username):
    return os.path.join(EVENTS_DIR, f"{username}.json")

@calendar_bp.route("/calendar", methods=["GET", "POST"])
@login_required
def calendar():
    session["last_form_page"] = "/calendar"

    if request.method == "POST":
        events_json = request.form.get("events_json")
        if events_json:
            try:
                os.makedirs(EVENTS_DIR, exist_ok=True)
                path = get_events_path(current_user.username)
                with open(path, "w") as f:
                    json.dump(json.loads(events_json), f)
            except Exception as e:
                print(f"❌ Failed to save events: {e}")

        if "go_home" in request.form:
            return redirect("/home")

    return render_template("calendar.html")

@calendar_bp.route("/api/events", methods=["GET", "POST"])
def events():
    # Coach or Player access
    if current_user.is_authenticated:
        username = current_user.username
    elif "player_code" in session:
        from blueprints.player import load_codes
        code = session["player_code"]
        codes = load_codes()
        username = codes.get(code, {}).get("created_by")
        if not username:
            return jsonify({"error": "Invalid code"}), 403
    else:
        return jsonify({"error": "Unauthorized"}), 401

    filepath = get_events_path(username)

    if request.method == "GET":
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return jsonify(json.load(f))
        return jsonify([])

    if request.method == "POST":
        if not current_user.is_authenticated:
            return jsonify({"error": "Only coaches can save events."}), 403

        try:
            events = request.json.get("events", [])
            os.makedirs(EVENTS_DIR, exist_ok=True)
            with open(filepath, "w") as f:
                json.dump(events, f)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": f"Failed to save events: {str(e)}"}), 500
