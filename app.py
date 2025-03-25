from flask import Flask, render_template, request, session
import json
import os

app = Flask(__name__)
app.secret_key = "secret_key"
SESSION_FILE = "saved_session.json"

def organize_matches(players, courts, match_type, num_matches):
    matchups = [[] for _ in range(courts)]
    match_counts = {p['name']: 0 for p in players}
    played_matches = {p['name']: set() for p in players}
    opponent_grades = {p['name']: [] for p in players}

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

    for round_num in range(num_matches):
        available_players = sorted(players, key=lambda p: match_counts[p['name']])
        used_names = set()
        round_matchups = []

        while len(round_matchups) < courts and len(available_players) - len(used_names) >= (4 if match_type == "doubles" else 2):
            if match_type == "doubles":
                group = []
                for _ in range(4):
                    for p in available_players:
                        if p['name'] not in used_names:
                            partner = find_best_partner(p, [q for q in available_players if q['name'] not in used_names and q['name'] != p['name']], round_num)
                            if partner:
                                group.extend([p, partner])
                                used_names.update([p['name'], partner['name']])
                                break
                    if len(group) == 4:
                        break
                if len(group) < 4:
                    break
                pair = group
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

            round_matchups.append((pair, False))

        for i, match in enumerate(round_matchups):
            matchups[i].append(match)

    return matchups, match_counts

@app.route("/", methods=["GET", "POST"])
def index():
    players = session.get("players", [])
    courts = session.get("courts", 1)
    num_matches = session.get("num_matches", 1)
    match_type = session.get("match_type", "singles")
    session_name = session.get("session_name", "")
    matchups = []
    player_match_counts = {}

    if request.method == "POST":
        if "remove_player" in request.form:
            name_to_remove = request.form.get("remove_player")
            players = [p for p in players if p["name"] != name_to_remove]
            session["players"] = players

        else:
            session_name = request.form.get("session_name", "")
            courts = int(request.form.get("courts", 1))
            num_matches = int(request.form.get("num_matches", 1))
            match_type = request.form.get("match_type", "singles")

            session["courts"] = courts
            session["num_matches"] = num_matches
            session["match_type"] = match_type
            session["session_name"] = session_name

            if "add_player" in request.form:
                name = request.form.get("name")
                grade = int(request.form.get("grade", 1))
                if name:
                    players.append({"name": name, "grade": grade})
                    session["players"] = players

            elif "organize_matches" in request.form:
                matchups, player_match_counts = organize_matches(players, courts, match_type, num_matches)

            elif "save_session" in request.form:
                with open(SESSION_FILE, "w") as f:
                    json.dump({
                        "players": players,
                        "courts": courts,
                        "num_matches": num_matches,
                        "match_type": match_type,
                        "session_name": session_name
                    }, f)

            elif "load_session" in request.form and os.path.exists(SESSION_FILE):
                with open(SESSION_FILE, "r") as f:
                    saved = json.load(f)
                    players = saved.get("players", [])
                    courts = saved.get("courts", 1)
                    num_matches = saved.get("num_matches", 1)
                    match_type = saved.get("match_type", "singles")
                    session_name = saved.get("session_name", "")
                    session.update(saved)

            elif "reset" in request.form:
                players = []
                matchups = []
                session.clear()

    return render_template(
        "index.html",
        players=players,
        matchups=matchups,
        courts=courts,
        num_matches=num_matches,
        match_type=match_type,
        session_name=session_name,
        player_match_counts=player_match_counts
    )

if __name__ == "__main__":
    app.run(debug=True)
