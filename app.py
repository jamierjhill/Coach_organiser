from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, session, jsonify, redirect
import os
import csv
from openai import OpenAI
from datetime import datetime, timedelta
import io
from collections import defaultdict
import random
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user


CSV_UPLOAD_PASSWORD = os.getenv("CSV_UPLOAD_PASSWORD")
COACHBOT_PASSWORD = os.getenv("COACHBOT_PASSWORD")
AI_TOOLBOX_PASSWORD = os.getenv("AI_TOOLBOX_PASSWORD")



app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------- Login System ----------------------------- #
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user


class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

    def get_id(self):
        return str(self.id)


# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirect here if not logged in

@login_manager.user_loader
def load_user(user_id):
    users = load_users()  # ✅ Load users inside this function
    for username in users:
        if str(username) == str(user_id):
            return User(id=username, username=username)
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        users = load_users()
        print("DEBUG: Attempt login", username, password)

        if username in users and users[username] == password:
            session["coach"] = username

            # ✅ Flask-Login logic: create and log in user
            user = User(id=username, username=username)
            login_user(user)

            print("DEBUG: Login success, redirecting to /home")
            return redirect("/home")

        print("DEBUG: Login failed")
        return render_template("login.html", error="Invalid credentials.")
    
    return render_template("login.html")




@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/login?message=You’ve been logged out successfully.")


# ----------------------------- initial load ----------------------------- #
@app.route("/")
def root():
    return redirect("/login")




# ----------------------------- Password Validation ----------------------------- #
@app.route("/validate-password", methods=["POST"])
def validate_password():
    data = request.get_json()
    if not data or "password" not in data:
        return jsonify(success=False, error="No password received.")

    if data["password"] == COACHBOT_PASSWORD:
        return jsonify(success=True)
    return jsonify(success=False, error="Incorrect password.")



# ----------------------------- Home Route ----------------------------- #

@app.route("/home")
@login_required
def home():
    return render_template("home.html")

# ----------------------------- Notes Route----------------------------- #
@app.route("/notes", methods=["GET", "POST"])
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


# ----------------------------- Calednar ----------------------------- #
@app.route("/calendar")
def calendar():
    if "coach" not in session:
        return redirect("/login")
    return render_template("calendar.html")


# ----------------------------- Users ----------------------------- #
import json


USERS_FILE = "data/users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        users = load_users()
        if username in users:
            return render_template("register.html", error="Username already exists.")

        users[username] = password  # Plain text for now
        save_users(users)

        session["coach"] = username

        # ✅ Mark coach as logged in for Flask-Login
        user = User(id=username, username=username)
        login_user(user)

        return redirect("/home")

    return render_template("register.html")



# ----------------------------- Events ----------------------------- #
from flask_login import login_required, current_user

@app.route("/api/events", methods=["GET", "POST"])
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


# ----------------------------- CoachBot ----------------------------- #
@app.route("/coachbot", methods=["GET", "POST"])
def coachbot_page():
    if not session.get("coachbot_access_granted"):
        if request.method == "POST" and "password" in request.form:
            if request.form["password"] == os.getenv("COACHBOT_PASSWORD"):
                session["coachbot_access_granted"] = True
                return redirect("/coachbot")
            else:
                return render_template("coachbot.html", error="Incorrect password")
        return render_template("coachbot.html")  # Show password form only

    return render_template("coachbot.html")  # Show chatbot UI if already unlocked

# ----------------------------- Link to guide ----------------------------- #
@app.route("/guide")
def guide():
    return render_template("coach_guide.html")

# ----------------------------- Match Organizer Function ----------------------------- #
def organize_matches(players, courts, match_type, num_matches):
    matchups = [[] for _ in range(courts)]
    match_counts = {p['name']: 0 for p in players}
    played_matches = {p['name']: set() for p in players}
    opponent_grades = {p['name']: [] for p in players}
    seen_doubles_matchups = set()
    previous_partners = {p['name']: set() for p in players}
    last_court_groups = {}

    def grade_distance(g1, g2):
        return abs(g1 - g2)

    def find_best_partner(player, candidates, round_num):
        grade_targets = opponent_grades[player['name']] or [player['grade']]
        sorted_candidates = sorted(
            candidates,
            key=lambda p: min(grade_distance(p['grade'], gt) for gt in grade_targets)
        )
        for candidate in sorted_candidates:
            if candidate['name'] != player['name'] and candidate['name'] not in played_matches[player['name']]:
                if candidate['name'] not in last_court_groups.get(player['name'], set()):
                    return candidate
        for candidate in sorted_candidates:
            if candidate['name'] != player['name']:
                return candidate
        return None

    def find_best_doubles_group(available, seen_matchups, last_court_groups):
        best_group = None
        best_diff = float('inf')
        best_match_key = None

        for i in range(len(available)):
            for j in range(i+1, len(available)):
                for k in range(len(available)):
                    for l in range(k+1, len(available)):
                        group = [available[i], available[j], available[k], available[l]]
                        names = [p['name'] for p in group]
                        if len(set(names)) < 4:
                            continue

                        team1 = [group[0], group[1]]
                        team2 = [group[2], group[3]]
                        team1_names = frozenset(p['name'] for p in team1)
                        team2_names = frozenset(p['name'] for p in team2)
                        match_key = frozenset([team1_names, team2_names])
                        full_group = frozenset(names)

                        if match_key in seen_matchups:
                            continue

                        if any(full_group == last_court_groups.get(p['name'], frozenset()) for p in group):
                            continue

                        team1_avg = sum(p['grade'] for p in team1) / 2
                        team2_avg = sum(p['grade'] for p in team2) / 2
                        diff = abs(team1_avg - team2_avg)

                        if diff < best_diff:
                            best_diff = diff
                            best_group = team1 + team2
                            best_match_key = match_key

        return (best_group, best_match_key) if best_group else (None, None)

    for round_num in range(num_matches):
        available_players = sorted(players, key=lambda p: match_counts[p['name']])
        random.shuffle(available_players)  # Add light randomness
        used_names = set()
        new_round_groups = {p['name']: set() for p in players}

        for court_index in range(courts):
            needed_players = 4 if match_type == "doubles" else 2
            if len(available_players) - len(used_names) < needed_players:
                continue

            candidates = [p for p in available_players if p['name'] not in used_names]

            if match_type == "doubles":
                group, match_key = find_best_doubles_group(
                    candidates, seen_doubles_matchups, last_court_groups
                )

                if not group:
                    continue

                seen_doubles_matchups.add(match_key)
                used_names.update(p['name'] for p in group)
                group_set = frozenset(p['name'] for p in group)

                for p in group:
                    last_court_groups[p['name']] = group_set
                    new_round_groups[p['name']].update(mate['name'] for mate in group if mate['name'] != p['name'])

                previous_partners[group[0]['name']].add(group[1]['name'])
                previous_partners[group[1]['name']].add(group[0]['name'])
                previous_partners[group[2]['name']].add(group[3]['name'])
                previous_partners[group[3]['name']].add(group[2]['name'])

                pair = group

            else:
                p1 = candidates.pop(0)
                p2 = find_best_partner(p1, candidates, round_num)
                if not p2:
                    continue
                used_names.update({p1['name'], p2['name']})
                pair = [p1, p2]
                new_round_groups[p1['name']].add(p2['name'])
                new_round_groups[p2['name']].add(p1['name'])

            for p in pair:
                match_counts[p['name']] += 1
                for opp in pair:
                    if opp['name'] != p['name']:
                        played_matches[p['name']].add(opp['name'])
                        opponent_grades[p['name']].append(opp['grade'])

            matchups[court_index].append((pair, round_num + 1))

    opponent_averages = {
        name: round(sum(grades) / len(grades), 2) if grades else 0
        for name, grades in opponent_grades.items()
    }

    opponent_diff = {
        name: round(abs(opponent_averages[name] - next(p['grade'] for p in players if p['name'] == name)), 2)
        for name in opponent_averages
    }

    return matchups, match_counts, opponent_averages, opponent_diff


# ----------------------------- Match Organiser Page Route ----------------------------- #
@app.route("/index", methods=["GET", "POST"])
def index():
    # Load session state
    players = session.get("players", [])
    courts = session.get("courts", 1)
    num_matches = session.get("num_matches", 1)
    match_type = session.get("match_type", "singles")
    session_name = session.get("session_name", "")
    view_mode = session.get("view_mode", "court")  # Default view

    # Defaults (may be overwritten)
    matchups = []
    player_match_counts = {}
    opponent_averages = {}
    opponent_diff = {}
    rounds = {}
    error = None

    if request.method == "POST":
        # Save session name
        session_name = request.form.get("session_name", "")
        session["session_name"] = session_name

        # Get updated settings
        try:
            courts = int(request.form.get("courts", courts))
            num_matches = int(request.form.get("num_matches", num_matches))
        except ValueError:
            pass

        match_type = request.form.get("match_type", match_type)
        view_mode = request.form.get("view_mode", view_mode)
        session.update({
            "courts": courts,
            "num_matches": num_matches,
            "match_type": match_type,
            "view_mode": view_mode
        })

        # Remove a player
        if "remove_player" in request.form:
            name_to_remove = request.form.get("remove_player")
            players = [p for p in players if p["name"] != name_to_remove]
            session["players"] = players

        # Upload CSV
        if "upload_csv" in request.form:
            csv_password = request.form.get("csv_password", "")
            if csv_password != CSV_UPLOAD_PASSWORD:
                error = "❌ Incorrect password for CSV upload."
            else:
                file = request.files.get("csv_file")
                if file and file.filename.endswith(".csv"):
                    try:
                        content = file.read().decode("utf-8")
                        reader = csv.DictReader(io.StringIO(content))
                        for row in reader:
                            name = row.get("name", "").strip()
                            try:
                                grade = int(row.get("grade", "").strip())
                            except (ValueError, AttributeError):
                                continue
                            if name and grade in [1, 2, 3, 4]:
                                players.append({"name": name, "grade": grade})
                        session["players"] = players
                    except Exception as e:
                        error = f"❌ Failed to read CSV: {str(e)}"
                else:
                    error = "⚠️ Please upload a valid .csv file."

            if error:
                return render_template(
                    "index.html",
                    error=error,
                    players=players,
                    courts=courts,
                    num_matches=num_matches,
                    match_type=match_type,
                    matchups=[],
                    player_match_counts={},
                    session_name=session_name,
                    rounds={},
                    view_mode=view_mode,
                    opponent_averages={},
                    opponent_diff={}
                )

        # Reset all
        elif "reset" in request.form:
            players = []
            matchups = []
            session.clear()

        # Add a single player
        elif "add_player" in request.form:
            name = request.form.get("name", "").strip()
            try:
                grade = int(request.form.get("grade"))
            except (TypeError, ValueError):
                grade = None

            if not name or grade not in [1, 2, 3, 4]:
                session["error"] = "Please enter a valid name and select a grade between 1 (strongest) and 4 (weakest)."
            else:
                players.append({"name": name, "grade": grade})
                session["players"] = players
                session.pop("error", None)

        # Organize or reshuffle matches
        if "organize_matches" in request.form or "reshuffle" in request.form:
            if "reshuffle" in request.form:
                random.shuffle(players)

            matchups, player_match_counts, opponent_averages, opponent_diff = organize_matches(
                players, courts, match_type, num_matches
            )

            # Build rounds
            round_structure = defaultdict(list)
            for court_index, court_matches in enumerate(matchups):
                for match, round_num in court_matches:
                    round_structure[round_num].append((court_index + 1, match))
            rounds = dict(sorted(round_structure.items()))

            # Save to session
            session["matchups"] = matchups
            session["player_match_counts"] = player_match_counts
            session["opponent_averages"] = opponent_averages
            session["opponent_diff"] = opponent_diff
            session["rounds"] = rounds

    else:
        # GET request: restore previous schedule
        matchups = session.get("matchups", [])
        player_match_counts = session.get("player_match_counts", {})
        opponent_averages = session.get("opponent_averages", {})
        opponent_diff = session.get("opponent_diff", {})
        rounds = session.get("rounds", {})

    return render_template(
        "index.html",
        players=players,
        matchups=matchups,
        courts=courts,
        num_matches=num_matches,
        match_type=match_type,
        session_name=session_name,
        player_match_counts=player_match_counts,
        opponent_averages=opponent_averages,
        opponent_diff=opponent_diff,
        error=session.pop("error", None),
        rounds=rounds,
        view_mode=view_mode
    )



# ----------------------------- ai toolbox ----------------------------- #
@app.route("/ai-toolbox", methods=["GET", "POST"])
def ai_toolbox():
    drill = None
    session_plan = None
    chat_response = None
    error = None

    # 🔒 Password gate
    if not session.get("ai_toolbox_access_granted"):
        if request.method == "POST" and "password" in request.form:
            if request.form["password"] == os.getenv("AI_TOOLBOX_PASSWORD"):
                session["ai_toolbox_access_granted"] = True
                return redirect("/ai-toolbox")
            else:
                error = "Incorrect password"
        return render_template("ai_toolbox.html", error=error)

    # ✅ If already unlocked, handle tool form logic
    if request.method == "POST" and "tool" in request.form:
        tool = request.form.get("tool")

        # DRILL TOOL
        if tool == "drill":
            drill_prompt = request.form.get("drill_prompt", "").strip()
            if drill_prompt:
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a tennis coach assistant that generates short, practical drills."},
                            {"role": "user", "content": drill_prompt}
                        ],
                        temperature=0.7
                    )
                    drill = response.choices[0].message.content.strip()
                except Exception as e:
                    error = f"Drill error: {e}"

        # SESSION TOOL
        elif tool == "session":
            players = request.form.get("players", "").strip()
            focus = request.form.get("focus", "").strip()
            duration = request.form.get("duration", "").strip()

            if players and focus and duration:
                try:
                    prompt = (
                        f"Create a tennis coaching session for {players} players. "
                        f"The focus is on {focus}. Duration: {duration} minutes. "
                        f"Include warm-up, main drills, and cool-down."
                    )
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a tennis coach assistant that creates practical and efficient session plans."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7
                    )
                    session_plan = response.choices[0].message.content.strip()
                except Exception as e:
                    error = f"Session plan error: {e}"

        # CHAT TOOL
        elif tool == "chat":
            chat_prompt = request.form.get("chat_prompt", "").strip()
            if chat_prompt:
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful tennis coaching assistant."},
                            {"role": "user", "content": chat_prompt}
                        ],
                        temperature=0.6
                    )
                    chat_response = response.choices[0].message.content.strip()
                except Exception as e:
                    error = f"CoachBot error: {e}"

    return render_template(
        "ai_toolbox.html",
        drill=drill,
        session_plan=session_plan,
        chat_response=chat_response,
        error=error
    )



# ----------------------------- Session Generator ----------------------------- #
@app.route("/session-generator", methods=["GET", "POST"])
def session_generator():
    session_plan = None

    # Password check
    if not session.get("session_access_granted"):
        if request.method == "POST" and "password" in request.form:
            if request.form["password"] == os.getenv("SESSION_PASSWORD"):
                session["session_access_granted"] = True
                return redirect("/session-generator")
            else:
                return render_template("session_generator.html", error="Incorrect password")
        return render_template("session_generator.html")  # Show password form only

    # Session generation
    if request.method == "POST" and "players" in request.form:
        players = request.form.get("players")
        focus = request.form.get("focus")
        duration = request.form.get("duration")

        prompt = (
            f"Create a tennis coaching session plan for {players} players. "
            f"The focus should be on {focus}, and the session should last {duration} minutes. "
            f"Include a warm-up, main drills, and a cool-down."
        )

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a tennis coach assistant that creates practical and efficient training sessions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            session_plan = response.choices[0].message.content.strip()
        except Exception as e:
            session_plan = f"⚠️ Error generating session: {str(e)}"

    return render_template("session_generator.html", session_plan=session_plan)

# ----------------------------- Log out session gen ----------------------------- #
@app.route("/logout-session-generator")
def logout_session_generator():
    session.pop("session_access_granted", None)
    return redirect("/session-generator")


# ----------------------------- Drill Generator ----------------------------- #
@app.route("/drill-generator", methods=["GET", "POST"])
def drill_generator():
    drill = None

    # Check password session
    if session.get("drill_access_granted") != True:
        if request.method == "POST":
            password = request.form.get("password", "")
            if password == os.getenv("DRILL_PASSWORD"):
                session["drill_access_granted"] = True
                return redirect("/drill-generator")
            else:
                return render_template("drill_generator.html", error="Incorrect password.")
        return render_template("drill_generator.html")  # show password form

    # If password accepted and prompt submitted
    if request.method == "POST" and "prompt" in request.form:
        prompt = request.form["prompt"]
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a tennis coach assistant that generates short, practical drills."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            drill = response.choices[0].message.content.strip()
        except Exception as e:
            drill = f"⚠️ Error generating drill: {str(e)}"

    return render_template("drill_generator.html", drill=drill)

# ----------------------------- logout drill gen ----------------------------- #
@app.route("/logout-drill-generator")
def logout_drill_generator():
    session.pop("drill_access_granted", None)
    return redirect("/drill-generator")


# ----------------------------- ChatBot ----------------------------- #
@app.route("/chatbot", methods=["POST"])
def chatbot():
    try:
        user_input = request.json.get("message", "")
        if not user_input:
            return jsonify({"success": False, "error": "❌ No message received."})

        now = datetime.now()
        if "chatbot_calls" not in session:
            session["chatbot_calls"] = []

        # Clean up old timestamps
        session["chatbot_calls"] = [
            t for t in session["chatbot_calls"]
            if datetime.fromisoformat(t) > now - timedelta(hours=1)
        ]

        if len(session["chatbot_calls"]) >= 10:
            return jsonify({
                "success": False,
                "error": "⏳ Limit reached: You’ve sent 10 messages this hour. Please wait before sending more."
            })

        # Track call
        session["chatbot_calls"].append(now.isoformat())
        session.modified = True

        # Start or retrieve conversation history
        if "chatbot_history" not in session:
            session["chatbot_history"] = [{
                "role": "system",
                "content": (
                    "You are a level 4 LTA tennis coaching assistant. "
                    "Keep answers concise, focused, and under 3 sentences. "
                    "Prompt the user to ask follow-ups (drills, advice, video)."
                )
            }]

        # Add user message
        session["chatbot_history"].append({"role": "user", "content": user_input})

        # Call OpenAI with full chat history
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=session["chatbot_history"],
            temperature=0.6
        )

        reply = response.choices[0].message.content.strip()

        # Save bot's reply
        session["chatbot_history"].append({"role": "assistant", "content": reply})
        session.modified = True

        return jsonify({"success": True, "reply": reply})

    except Exception as e:
        return jsonify({"success": False, "error": "⚠️ The AI coach encountered an error."})




# ----------------------------- Contact Page ----------------------------- #
@app.route("/contact")
def contact():
    return render_template("contact.html")



if __name__ == "__main__":
    app.run(debug=True)
