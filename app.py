from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, session, jsonify
import os
import csv
from openai import OpenAI
from datetime import datetime, timedelta
import io


CSV_UPLOAD_PASSWORD = os.getenv("CSV_UPLOAD_PASSWORD")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")  # ✅ this is the one you want

SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------- Match Organizer Function ----------------------------- #
def organize_matches(players, courts, match_type, num_matches):
    matchups = [[] for _ in range(courts)]
    match_counts = {p['name']: 0 for p in players}
    played_matches = {p['name']: set() for p in players}
    opponent_grades = {p['name']: [] for p in players}
    seen_doubles_matchups = set()
    previous_partners = {p['name']: set() for p in players}

    def grade_distance(g1, g2):
        return abs(g1 - g2)

    def find_best_partner(player, candidates, round_num):
        grade_targets = [player['grade']] if round_num == 0 else opponent_grades[player['name']]
        if not grade_targets:
            grade_targets = [player['grade']]
        sorted_candidates = sorted(
            candidates,
            key=lambda p: min(grade_distance(p['grade'], gt) for gt in grade_targets)
        )
        for candidate in sorted_candidates:
            if candidate['name'] != player['name'] and candidate['name'] not in played_matches[player['name']]:
                return candidate
        for candidate in sorted_candidates:
            if candidate['name'] != player['name']:
                return candidate
        return None

    def find_best_doubles_group(available, seen_matchups):
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

                        if match_key in seen_matchups:
                            continue

                        if any(p2['name'] in previous_partners[p1['name']] for p1, p2 in [(team1[0], team1[1]), (team2[0], team2[1])]):
                            continue

                        team1_avg = sum(p['grade'] for p in team1) / 2
                        team2_avg = sum(p['grade'] for p in team2) / 2
                        diff = abs(team1_avg - team2_avg)

                        if diff < best_diff:
                            best_diff = diff
                            best_group = team1 + team2
                            best_match_key = match_key

        return best_group, best_match_key if best_group else (None, None)

    for round_num in range(num_matches):
        available_players = sorted(players, key=lambda p: match_counts[p['name']])
        used_names = set()
        round_matchups = []

        while len(round_matchups) < courts and len(available_players) - len(used_names) >= (4 if match_type == "doubles" else 2):
            if match_type == "doubles":
                candidates = [p for p in available_players if p['name'] not in used_names]
                group, match_key = find_best_doubles_group(candidates, seen_doubles_matchups)
                if not group:
                    break
                seen_doubles_matchups.add(match_key)
                used_names.update(p['name'] for p in group)
                pair = group
                previous_partners[group[0]['name']].add(group[1]['name'])
                previous_partners[group[1]['name']].add(group[0]['name'])
                previous_partners[group[2]['name']].add(group[3]['name'])
                previous_partners[group[3]['name']].add(group[2]['name'])
            else:
                p1 = next((p for p in available_players if p['name'] not in used_names), None)
                if not p1:
                    break
                p2 = find_best_partner(p1, [p for p in available_players if p['name'] not in used_names and p['name'] != p1['name']], round_num)
                if not p2:
                    break
                pair = [p1, p2]
                used_names.update([p1['name'], p2['name']])

            for p in pair:
                match_counts[p['name']] += 1
                for opp in pair:
                    if opp['name'] != p['name']:
                        played_matches[p['name']].add(opp['name'])
                        opponent_grades[p['name']].append(opp['grade'])

            round_matchups.append((pair, round_num + 1))

        for i, match in enumerate(round_matchups):
            matchups[i].append(match)

    opponent_averages = {
        name: round(sum(grades) / len(grades), 2) if grades else 0
        for name, grades in opponent_grades.items()
    }

    opponent_diff = {
        name: round(abs(opponent_averages[name] - next(p['grade'] for p in players if p['name'] == name)), 2)
        for name in opponent_averages
    }

    return matchups, match_counts, opponent_averages, opponent_diff

# ----------------------------- Main Page ----------------------------- #
@app.route("/", methods=["GET", "POST"])
def index():
    players = session.get("players", [])
    courts = session.get("courts", 1)
    num_matches = session.get("num_matches", 1)
    match_type = session.get("match_type", "singles")
    session_name = session.get("session_name", "")
    matchups = []
    player_match_counts = {}
    opponent_averages = {}
    opponent_diff = {}
    error = None

    if request.method == "POST":
        session_name = request.form.get("session_name", "")
        session["session_name"] = session_name

        try:
            courts = int(request.form.get("courts", session.get("courts", 1)))
            num_matches = int(request.form.get("num_matches", session.get("num_matches", 1)))
        except ValueError:
            courts = session.get("courts", 1)
            num_matches = session.get("num_matches", 1)

        match_type = request.form.get("match_type", session.get("match_type", "singles"))

        session.update({
            "courts": courts,
            "num_matches": num_matches,
            "match_type": match_type
        })

        if "remove_player" in request.form:
            name_to_remove = request.form.get("remove_player")
            players = [p for p in players if p["name"] != name_to_remove]
            session["players"] = players

        if "upload_csv" in request.form:
            csv_password = request.form.get("csv_password", "")
            print(f"Submitted password: {csv_password}")
            print(f"Expected password: {CSV_UPLOAD_PASSWORD}")

            if csv_password != CSV_UPLOAD_PASSWORD:
                error = "❌ Incorrect password for CSV upload."
            else:
                if "csv_file" in request.files:
                    file = request.files["csv_file"]
                    print("CSV file uploaded:", file.filename)
                    if file and file.filename.endswith(".csv"):
                        try:
                            content = file.read().decode("utf-8")
                            reader = csv.DictReader(io.StringIO(content))
                            for row in reader:
                                print("Parsed row:", row)
                                name = row.get("name", "").strip()
                                try:
                                    grade = int(row.get("grade", "").strip())
                                except (ValueError, AttributeError):
                                    print("Invalid grade for row:", row)
                                    continue
                                if name and grade in [1, 2, 3, 4]:
                                    players.append({"name": name, "grade": grade})
                            session["players"] = players
                        except Exception as e:
                            error = f"❌ Failed to read CSV: {str(e)}"
                    else:
                        error = "⚠️ Please upload a valid .csv file."
                else:
                    error = "⚠️ No CSV file found in upload."

            if error:
                return render_template(
                    "index.html",
                    error=error,
                    players=players,
                    courts=courts,
                    num_matches=num_matches,
                    match_type=match_type,
                    matchups=matchups,
                    player_match_counts=player_match_counts,
                    session_name=session_name
                )

        elif "reset" in request.form:
            players = []
            matchups = []
            session.clear()

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

        if "organize_matches" in request.form or "reshuffle" in request.form:
            matchups, player_match_counts, opponent_averages, opponent_diff = organize_matches(
                players, courts, match_type, num_matches
            )

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
        error=session.pop("error", None)
    )


# ----------------------------- Link to guide ----------------------------- #
@app.route("/guide")
def guide():
    return render_template("coach_guide.html")


# ----------------------------- Practice Drill Generator ----------------------------- #
@app.route("/generate_drills", methods=["POST"])
def generate_drills():
    try:
        # ✅ Password protection
        password = request.form.get("drill_password", "")
        correct_password = os.getenv("DRILL_PASSWORD", "letmein")
        if password != correct_password:
            return jsonify({"success": False, "error": "🔒 Access denied. Incorrect password."})

        # ✅ Rate limiting (5 per hour per session)
        now = datetime.now()
        if "drill_calls" not in session:
            session["drill_calls"] = []

        # Clean old calls
        session["drill_calls"] = [
            t for t in session["drill_calls"]
            if datetime.fromisoformat(t) > now - timedelta(hours=1)
        ]

        if len(session["drill_calls"]) >= 5:
            return jsonify({"success": False, "error": "⏱️ You've hit the limit (5 drills/hour). Please wait before trying again."})

        session["drill_calls"].append(now.isoformat())
        session.modified = True

        # Extract form inputs
        num_players = request.form.get("drill_players", "8")
        format_type = request.form.get("drill_format", "doubles")
        focus_area = request.form.get("focus_area", "net play")
        time = request.form.get("drill_time", "30")

        # Create prompt
        prompt = f"""
        You are a professional tennis coach. Create a warm-up and practice drill plan for a session with these settings:
        - Number of Players: {num_players}
        - Format: {format_type}
        - Focus Area: {focus_area}
        - Total Time: {time} minutes

        Suggest 2–3 creative, court-efficient, engaging drills. Include names, durations, setup, instructions, and purpose.
        """

        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a tennis coaching assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        drills_text = response.choices[0].message.content or ""
        if len(drills_text) > 2000:
            drills_text = drills_text[:2000] + "\n\n...(truncated)"

        # ✅ Return response early — no writes after this
        return jsonify({"success": True, "drills": drills_text})

    except Exception as e:
        # Log error to file (avoiding stdout)
        import logging, traceback
        logging.basicConfig(filename='/tmp/app.log', level=logging.ERROR)
        logging.error("Drill generation error: %s", traceback.format_exc())
        return jsonify({"success": False, "error": "⚠️ Something went wrong while generating drills."})




# ----------------------------- Run App ----------------------------- #
if __name__ == "__main__":
    app.run(debug=True)
