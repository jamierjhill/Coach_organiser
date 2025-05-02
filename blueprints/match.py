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
    view_mode = session.get("view_mode", "round")

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
            
            # Convert all round keys to integers to ensure consistency
            rounds_int_keys = {}
            for k, v in current_rounds.items():
                try:
                    rounds_int_keys[int(k)] = v
                except (ValueError, TypeError):
                    continue
            current_rounds = rounds_int_keys
            
            if round_to_reshuffle in current_rounds:
                # Get the original matches to preserve exact structure
                original_matches = current_rounds[round_to_reshuffle]
                
                # Debug: Print original structure
                print(f"Original matches in round {round_to_reshuffle}: {len(original_matches)} matches")
                for court_num, match in original_matches:
                    print(f"Court {court_num}: {len(match)} players")
                
                # Get all unique players in this round
                all_players = []
                seen_players = set()
                for court_num, match in original_matches:
                    for player in match:
                        player_name = player['name']
                        if player_name not in seen_players:
                            all_players.append(player)
                            seen_players.add(player_name)
                
                print(f"Total unique players: {len(all_players)}")
                
                # Shuffle all players
                random.shuffle(all_players)
                
                # Recreate matches with the EXACT same structure
                new_round_matches = []
                player_idx = 0
                
                for court_num, original_match in original_matches:
                    match_size = len(original_match)
                    if player_idx + match_size <= len(all_players):
                        new_match = all_players[player_idx:player_idx + match_size]
                        new_round_matches.append((court_num, new_match))
                        player_idx += match_size
                
                print(f"New matches created: {len(new_round_matches)}")
                
                # Update the rounds structure
                current_rounds[round_to_reshuffle] = new_round_matches
                
                # Update the matchups structure
                # First, clear the matches for this round from all courts
                for court_matches in current_matchups:
                    court_matches[:] = [(match, rnd) for match, rnd in court_matches if rnd != round_to_reshuffle]
                
                # Then add the new matches back to the appropriate courts
                for court_num, match in new_round_matches:
                    current_matchups[court_num - 1].append((match, round_to_reshuffle))
                
                # Sort matches within each court by round number
                for court_matches in current_matchups:
                    court_matches.sort(key=lambda x: int(x[1]))
                
                # Update session with clean data
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