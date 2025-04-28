from flask import Blueprint, render_template, request, session, redirect
from flask_login import login_required, current_user
import random, os, csv, io
from collections import defaultdict
from utils import organize_matches

match_bp = Blueprint("match", __name__)

@match_bp.route("/index", methods=["GET", "POST"])
def index():
    session["last_form_page"] = "/index"  # 🧠 Smart Save & Home tracking

    players = session.get("players", [])
    courts = session.get("courts", 1)
    num_matches = session.get("num_matches", 1)
    match_type = session.get("match_type", "singles")
    session_name = session.get("session_name", "")
    view_mode = session.get("view_mode", "court")

    matchups = []
    player_match_counts = {}
    opponent_averages = {}
    opponent_diff = {}
    rounds = {}
    error = None

    if request.method == "POST":
        session_name = request.form.get("session_name", "")
        session["session_name"] = session_name

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

        if "remove_player" in request.form:
            name_to_remove = request.form.get("remove_player")
            players = [p for p in players if p["name"] != name_to_remove]
            session["players"] = players

        if "upload_csv" in request.form:
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
            if "reshuffle" in request.form:
                random.shuffle(players)

            matchups, player_match_counts, opponent_averages, opponent_diff = organize_matches(
                players, courts, match_type, num_matches
            )

            round_structure = defaultdict(list)
            for court_index, court_matches in enumerate(matchups):
                for match, round_num in court_matches:
                    round_structure[round_num].append((court_index + 1, match))
            rounds = dict(sorted(round_structure.items()))

            session["matchups"] = matchups
            session["player_match_counts"] = player_match_counts
            session["opponent_averages"] = opponent_averages
            session["opponent_diff"] = opponent_diff
            session["rounds"] = rounds

        if "go_home" in request.form:
            return redirect("/home")

    else:
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