from flask import Flask, render_template, request, session
import json
import os

app = Flask(__name__)
app.secret_key = "secret_key"
SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

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

    def find_best_doubles_group(available):
        best_group = None
        best_diff = float('inf')

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
                        team1_avg = sum(p['grade'] for p in team1) / 2
                        team2_avg = sum(p['grade'] for p in team2) / 2
                        diff = abs(team1_avg - team2_avg)
                        if diff < best_diff:
                            best_diff = diff
                            best_group = group
        return best_group

    for round_num in range(num_matches):
        available_players = sorted(players, key=lambda p: match_counts[p['name']])
        used_names = set()
        round_matchups = []

        while len(round_matchups) < courts and len(available_players) - len(used_names) >= (4 if match_type == "doubles" else 2):
            if match_type == "doubles":
                candidates = [p for p in available_players if p['name'] not in used_names]
                group = find_best_doubles_group(candidates)
                if not group:
                    break
                used_names.update(p['name'] for p in group)
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

            round_matchups.append((pair, round_num + 1))

        for i, match in enumerate(round_matchups):
            matchups[i].append(match)

    opponent_averages = {
        name: round(sum(grades)/len(grades), 2) if grades else 0
        for name, grades in opponent_grades.items()
    }

    opponent_diff = {
        name: round(abs(opponent_averages[name] - next(p['grade'] for p in players if p['name'] == name)), 2)
        for name in opponent_averages
    }

    return matchups, match_counts, opponent_averages, opponent_diff

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

            session.update({
                "courts": courts,
                "num_matches": num_matches,
                "match_type": match_type,
                "session_name": session_name
            })

            if "add_player" in request.form:
                name = request.form.get("name")
                grade = int(request.form.get("grade", 1))
                if name:
                    players.append({"name": name, "grade": grade})
                    session["players"] = players

            elif "organize_matches" in request.form:
                matchups, player_match_counts, opponent_averages, opponent_diff = organize_matches(players, courts, match_type, num_matches)

            elif "save_session" in request.form and session_name:
                file_path = os.path.join(SESSIONS_DIR, f"{session_name}.json")
                with open(file_path, "w") as f:
                    json.dump({
                        "players": players,
                        "courts": courts,
                        "num_matches": num_matches,
                        "match_type": match_type,
                        "session_name": session_name
                    }, f)

            elif "load_session" in request.form and session_name:
                file_path = os.path.join(SESSIONS_DIR, f"{session_name}.json")
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
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
        player_match_counts=player_match_counts,
        opponent_averages=opponent_averages,
        opponent_diff=opponent_diff
    )

if __name__ == "__main__":
    app.run(debug=True)
