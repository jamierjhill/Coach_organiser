from flask import Blueprint, render_template, request, session, redirect
from flask_login import login_required, current_user
import random, os, csv, io
from collections import defaultdict
from utils import organize_matches

match_bp = Blueprint("match", __name__)

@match_bp.route("/index", methods=["GET", "POST"])
@login_required
def index():
    # Add this check
    if not current_user.is_authenticated:
        return redirect("/login")
        
    session["last_form_page"] = "/index"

    players = session.get("players", [])
    courts = session.get("courts", 1)
    num_matches = session.get("num_matches", 1)
    match_type = session.get("match_type", "singles")
    session_name = session.get("session_name", "")
    view_mode = session.get("view_mode", "court")

    matchups = session.get("matchups", [])
    player_match_counts = session.get("player_match_counts", {})
    opponent_averages = session.get("opponent_averages", {})
    opponent_diff = session.get("opponent_diff", {})
    rounds = session.get("rounds", {})
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

        elif "upload_csv" in request.form:
            try:
                file = request.files.get("csv_file")
                if not file:
                    error = "⚠️ No file selected."
                elif not file.filename.endswith(".csv"):
                    error = "⚠️ Please upload a valid .csv file."
                else:
                    try:
                        content = file.read().decode("utf-8")
                        reader = csv.DictReader(io.StringIO(content))
                        
                        # Validate CSV structure before processing
                        if not reader.fieldnames or 'name' not in reader.fieldnames or 'grade' not in reader.fieldnames:
                            error = "⚠️ CSV must have 'name' and 'grade' columns."
                        else:
                            added_count = 0
                            for row in reader:
                                name = row.get("name", "").strip()
                                try:
                                    grade = int(row.get("grade", "").strip())
                                except (ValueError, AttributeError):
                                    continue
                                if name and grade in [1, 2, 3, 4]:
                                    players.append({"name": name, "grade": grade})
                                    added_count += 1
                            
                            if added_count == 0:
                                error = "⚠️ No valid players found in CSV."
                            else:
                                session["players"] = players
                                # Explicitly save the session
                                session.modified = True
                                
                    except UnicodeDecodeError:
                        error = "⚠️ File encoding error. Please ensure the CSV is UTF-8 encoded."
                    except Exception as e:
                        error = f"❌ Failed to read CSV: {str(e)}"
                        # Log the error for debugging
                        print(f"CSV Upload Error: {str(e)}")
            
            except Exception as e:
                error = f"❌ Unexpected error during file upload: {str(e)}"
                print(f"File Upload Error: {str(e)}")
            
            # Ensure we're still logged in
            if not current_user.is_authenticated:
                print("User was logged out during CSV upload!")
                return redirect("/login")

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
                    session_name=session_name,
                    rounds=rounds,
                    view_mode=view_mode,
                    opponent_averages=opponent_averages,
                    opponent_diff=opponent_diff
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

        elif "reshuffle_round" in request.form:
            round_to_reshuffle = int(request.form.get("reshuffle_round"))
            
            # Ensure we have the current data
            current_matchups = session.get("matchups", [])
            current_rounds = session.get("rounds", {})
            
            if round_to_reshuffle in current_rounds:
                # Get all players in this round
                players_in_round = []
                for court_num, match in current_rounds[round_to_reshuffle]:
                    players_in_round.extend(match)
                
                # Shuffle only these players
                random.shuffle(players_in_round)
                
                # Reconstruct matches for this round
                new_round_matches = []
                court_idx = 0
                
                if match_type == "doubles":
                    # Create new doubles matches
                    for i in range(0, len(players_in_round), 4):
                        if i + 3 < len(players_in_round):
                            match = players_in_round[i:i+4]
                            new_round_matches.append((court_idx + 1, match))
                            court_idx += 1
                else:
                    # Create new singles matches
                    for i in range(0, len(players_in_round), 2):
                        if i + 1 < len(players_in_round):
                            match = [players_in_round[i], players_in_round[i+1]]
                            new_round_matches.append((court_idx + 1, match))
                            court_idx += 1
                
                # Update the rounds structure
                current_rounds[round_to_reshuffle] = new_round_matches
                
                # Update the matchups structure
                # First, clear the matches for this round from all courts
                for court_matches in current_matchups:
                    court_matches[:] = [(match, rnd) for match, rnd in court_matches if rnd != round_to_reshuffle]
                
                # Then add the new matches back to the appropriate courts
                for court_num, match in new_round_matches:
                    if court_num <= len(current_matchups):
                        current_matchups[court_num - 1].append((match, round_to_reshuffle))
                
                # Sort matches within each court by round number
                for court_matches in current_matchups:
                    court_matches.sort(key=lambda x: x[1])
                
                # Update session
                session["matchups"] = current_matchups
                session["rounds"] = current_rounds
                matchups = current_matchups
                rounds = current_rounds

        elif "reshuffle_court" in request.form:
            court_to_reshuffle = int(request.form.get("reshuffle_court"))
            
            # Ensure we have the current data
            current_matchups = session.get("matchups", [])
            current_rounds = session.get("rounds", {})
            
            if court_to_reshuffle <= len(current_matchups):
                # Get all matches on this court
                court_matches = current_matchups[court_to_reshuffle - 1]
                
                # Extract all players from all matches on this court
                players_on_court = []
                round_assignments = []
                
                for match, round_num in court_matches:
                    players_on_court.extend(match)
                    round_assignments.append(round_num)
                
                # Shuffle players
                random.shuffle(players_on_court)
                
                # Reconstruct matches for this court
                new_court_matches = []
                player_idx = 0
                
                if match_type == "doubles":
                    # Create new doubles matches
                    for round_num in round_assignments:
                        if player_idx + 3 < len(players_on_court):
                            match = players_on_court[player_idx:player_idx+4]
                            new_court_matches.append((match, round_num))
                            player_idx += 4
                else:
                    # Create new singles matches
                    for round_num in round_assignments:
                        if player_idx + 1 < len(players_on_court):
                            match = [players_on_court[player_idx], players_on_court[player_idx+1]]
                            new_court_matches.append((match, round_num))
                            player_idx += 2
                
                # Update the matchups for this court
                current_matchups[court_to_reshuffle - 1] = new_court_matches
                
                # Update the rounds structure
                for round_num in current_rounds:
                    # Remove matches for this court from the round
                    current_rounds[round_num] = [(c, m) for c, m in current_rounds[round_num] if c != court_to_reshuffle]
                    
                    # Add the new matches for this court to the appropriate rounds
                    for match, match_round in new_court_matches:
                        if match_round == round_num:
                            current_rounds[round_num].append((court_to_reshuffle, match))
                    
                    # Sort by court number
                    current_rounds[round_num].sort(key=lambda x: x[0])
                
                # Update session
                session["matchups"] = current_matchups
                session["rounds"] = current_rounds
                matchups = current_matchups
                rounds = current_rounds

        elif "organize_matches" in request.form or "reshuffle" in request.form:
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

    # Always use the latest session data for rendering
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