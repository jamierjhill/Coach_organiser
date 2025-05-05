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

        # Handle editing player rounds
        if "edit_player_rounds" in request.form:
            player_name = request.form.get("edit_player_name")
            try:
                max_rounds = int(request.form.get("max_rounds", num_matches))
                # Find the player in the list and update max_rounds
                for player in players:
                    if player["name"] == player_name:
                        if max_rounds < num_matches:
                            player["max_rounds"] = max_rounds
                        else:
                            # If max_rounds is equal to or greater than num_matches, 
                            # remove the restriction
                            if "max_rounds" in player:
                                del player["max_rounds"]
                        break
                session["players"] = players
            except (ValueError, TypeError):
                pass

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
                # Remove the matches for this round
                for court_matches in current_matchups:
                    court_matches[:] = [(match, rnd) for match, rnd in court_matches if rnd != round_to_reshuffle]
                
                # Update the session before reorganizing this round
                session["matchups"] = current_matchups
                session["rounds"] = {k: v for k, v in current_rounds.items() if k != round_to_reshuffle}
                
                # Recalculate player match counts
                all_players = session.get("players", [])
                player_match_counts = {p['name']: 0 for p in all_players}
                for court_matches in current_matchups:
                    for match, round_num in court_matches:
                        for player in match:
                            player_match_counts[player['name']] += 1
                
                session["player_match_counts"] = player_match_counts
                
                # Now call the organize_matches function for just this round
                # This is a simplified version to organize just one round
                def organize_single_round(players, courts, match_type, round_num, current_player_match_counts):
                    # Filter players based on their max_rounds constraint
                    # Only include players who haven't reached their match limit
                    available_players = [
                        p for p in players 
                        if current_player_match_counts[p['name']] < p.get('max_rounds', num_matches) and
                           round_num <= p.get('max_rounds', num_matches)
                    ]
                    
                    # Sort available players by:
                    # 1. Limited players first (players with max_rounds < num_matches)
                    # 2. Players with fewer remaining rounds
                    # 3. Players who have played fewer matches so far
                    available_players.sort(key=lambda p: (
                        # Primary: Unlimited players last (False sorts before True)
                        p.get('max_rounds', num_matches) >= num_matches,
                        # Secondary: Sort by remaining rounds (fewer remaining rounds first)
                        p.get('max_rounds', num_matches) - round_num + 1,
                        # Tertiary: Sort by matches played so far (fewer played first)
                        current_player_match_counts[p['name']]
                    ))
                    
                    # Add some randomness while maintaining priority
                    import random
                    
                    # Group players by priority
                    priority_groups = {}
                    for player in available_players:
                        priority_key = (
                            player.get('max_rounds', num_matches) >= num_matches,
                            player.get('max_rounds', num_matches) - round_num + 1,
                            current_player_match_counts[player['name']]
                        )
                        if priority_key not in priority_groups:
                            priority_groups[priority_key] = []
                        priority_groups[priority_key].append(player)
                    
                    # Shuffle each priority group separately
                    for players_group in priority_groups.values():
                        random.shuffle(players_group)
                    
                    # Rebuild the available_players list
                    available_players = []
                    for key in sorted(priority_groups.keys()):
                        available_players.extend(priority_groups[key])
                    
                    # Create matches for this round
                    round_matches = []
                    used_names = set()
                    
                    # Determine how many players we need per match
                    players_per_match = 2 if match_type == "singles" else 4
                    
                    for court_num in range(1, courts + 1):
                        # Get players who haven't been used in this round yet
                        remaining_players = [p for p in available_players if p['name'] not in used_names]
                        
                        if len(remaining_players) >= players_per_match:
                            # Just take the next available players based on our prioritized order
                            match_players = remaining_players[:players_per_match]
                            round_matches.append((court_num, match_players))
                            
                            # Mark these players as used
                            used_names.update(p['name'] for p in match_players)
                            
                            # Update player match counts
                            for player in match_players:
                                current_player_match_counts[player['name']] += 1
                    
                    return round_matches, current_player_match_counts
                
                # Create new matches for this round
                new_round_matches, updated_match_counts = organize_single_round(
                    all_players, courts, match_type, round_to_reshuffle, player_match_counts
                )
                
                # Update player match counts
                session["player_match_counts"] = updated_match_counts
                
                # Update the rounds structure
                current_rounds[round_to_reshuffle] = new_round_matches
                
                # Add the new matches back to the court structure
                for court_num, match in new_round_matches:
                    if court_num <= len(current_matchups):
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
