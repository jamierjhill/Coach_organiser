import os, json
from flask import Blueprint, render_template, jsonify, request, session, redirect, Response
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
    try:
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
            try:
                if os.path.exists(filepath):
                    with open(filepath, "r") as f:
                        return jsonify(json.load(f))
                return jsonify([])
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid data format"}), 500
            except Exception as e:
                return jsonify({"error": f"Failed to load events: {str(e)}"}), 500

        if request.method == "POST":
            if not current_user.is_authenticated:
                return jsonify({"error": "Only coaches can save events."}), 403

            try:
                events = request.json.get("events", [])
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w") as f:
                    json.dump(events, f)
                return jsonify({"success": True})
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON format"}), 400
            except Exception as e:
                return jsonify({"error": f"Failed to save events: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@calendar_bp.route("/calendar/export")
@login_required
def export_calendar():
    coach = current_user.username
    filepath = os.path.join("data/events", f"{coach}.json")

    if not os.path.exists(filepath):
        return Response("No events found.", status=404)

    try:
        with open(filepath, "r") as f:
            events = json.load(f)

        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//CoachHub Calendar//EN"
        ]

        for event in events:
            # Sanitize event data
            event_id = str(event.get('id', uuid.uuid4())).replace("\n", "")
            start = event.get('start', '').replace("-", "").replace(":", "").replace("T", "T") + "Z"
            end = event.get('end', '').replace("-", "").replace(":", "").replace("T", "T") + "Z" if event.get('end') else start
            title = event.get('title', 'Untitled Event').replace("\n", " ")
            
            ics_lines += [
                "BEGIN:VEVENT",
                f"UID:{event_id}@coachhub",
                f"DTSTAMP:{start}",
                f"DTSTART:{start}",
                f"DTEND:{end}",
                f"SUMMARY:{title}",
                "END:VEVENT"
            ]

        ics_lines.append("END:VCALENDAR")
        ics_content = "\r\n".join(ics_lines)

        response = Response(
            ics_content,
            mimetype="text/calendar",
            headers={
                "Content-Disposition": f"attachment; filename=coaching_calendar_{coach}.ics",
                "Content-Type": "text/calendar; charset=utf-8",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff"
            }
        )
        return response
    except Exception as e:
        print(f"❌ Error exporting calendar: {e}")
        return Response(f"Error exporting calendar: {str(e)}", status=500)