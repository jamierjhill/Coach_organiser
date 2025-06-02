# app.py - Simplified Tennis Match Organizer
from dotenv import load_dotenv
load_dotenv()

import os, random, csv, io
from datetime import timedelta
from collections import defaultdict
from flask import Flask, render_template, request, session, redirect
from utils import organize_matches

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_key_UNSAFE_FOR_PRODUCTION")

# Session configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

def reshuffle_single_round(players, courts, match_type, round_to_reshuffle, existing_matchups, existing_rounds):
    """
    Reshuffle a specific round while preserving other rounds. More flexible algorithm that allows multiple reshuffles.
    """
    # Find players available for this round
    available_players = []
    for player in players:
        max_rounds = player.get('max_rounds', len(existing_rounds))
        if round_to_reshuffle <= max_rounds:
            available_players.append(player)
    
    if len(available_players) < (4 if match_type == "doubles" else 2):
        return None  # Not enough players for reshuffling
    
    # Shuffle available players for maximum randomness
    random.shuffle(available_players)
    
    # Track existing combinations from OTHER rounds (not the one we're reshuffling)
    # We'll use this as preference, not strict blocking
    existing_combinations = set()
    if match_type == "doubles":
        for court_matches in existing_matchups:
            for match, round_num in court_matches:
                if round_num != round_to_reshuffle and len(match) == 4:
                    # Store all possible team combinations
                    names = [p['name'] for p in match]
                    # Try different team splits
                    team1 = frozenset([names[0], names[1]])
                    team2 = frozenset([names[2], names[3]])
                    existing_combinations.add(frozenset([team1, team2]))
                    
                    team1 = frozenset([names[0], names[2]])
                    team2 = frozenset([names[1], names[3]])
                    existing_combinations.add(frozenset([team1, team2]))
                    
                    team1 = frozenset([names[0], names[3]])
                    team2 = frozenset([names[1], names[2]])
                    existing_combinations.add(frozenset([team1, team2]))
    else:  # singles
        for court_matches in existing_matchups:
            for match, round_num in court_matches:
                if round_num != round_to_reshuffle and len(match) == 2:
                    pair = frozenset([match[0]['name'], match[1]['name']])
                    existing_combinations.add(pair)
    
    # Generate new matches for this round
    new_round_matches = []
    used_players = set()
    
    def grade_distance(g1, g2):
        return abs(g1 - g2)
    
    def create_singles_match(candidates):
        """Create a singles match, preferring new combinations"""
        if len(candidates) < 2:
            return None
            
        best_pair = None
        best_score = float('inf')
        
        for i in range(len(candidates)):
            for j in range(i+1, len(candidates)):
                p1, p2 = candidates[i], candidates[j]
                pair_key = frozenset([p1['name'], p2['name']])
                
                # Score this pairing
                grade_diff = grade_distance(p1['grade'], p2['grade'])
                
                # Bonus for new combinations (but don't block old ones completely)
                novelty_bonus = 0 if pair_key in existing_combinations else -2
                
                score = grade_diff + novelty_bonus
                
                if score < best_score:
                    best_score = score
                    best_pair = [p1, p2]
        
        return best_pair
    
    def create_doubles_match(candidates):
        """Create a doubles match, preferring new combinations"""
        if len(candidates) < 4:
            return None
            
        best_group = None
        best_score = float('inf')
        
        # Try different combinations of 4 players
        for i in range(len(candidates)):
            for j in range(i+1, len(candidates)):
                for k in range(len(candidates)):
                    for l in range(k+1, len(candidates)):
                        if len(set([i, j, k, l])) != 4:
                            continue
                            
                        group = [candidates[i], candidates[j], candidates[k], candidates[l]]
                        
                        # Try this as team1 vs team2
                        team1 = [group[0], group[1]]
                        team2 = [group[2], group[3]]
                        
                        team1_avg = (team1[0]['grade'] + team1[1]['grade']) / 2
                        team2_avg = (team2[0]['grade'] + team2[1]['grade']) / 2
                        grade_diff = abs(team1_avg - team2_avg)
                        
                        # Check if this combination exists
                        team1_names = frozenset([team1[0]['name'], team1[1]['name']])
                        team2_names = frozenset([team2[0]['name'], team2[1]['name']])
                        match_key = frozenset([team1_names, team2_names])
                        
                        # Bonus for new combinations
                        novelty_bonus = 0 if match_key in existing_combinations else -3
                        
                        score = grade_diff + novelty_bonus
                        
                        if score < best_score:
                            best_score = score
                            best_group = group
        
        return best_group
    
    # Create matches for each court
    for court_index in range(courts):
        remaining_players = [p for p in available_players if p['name'] not in used_players]
        
        if match_type == "singles":
            match = create_singles_match(remaining_players)
            if match:
                new_round_matches.append((court_index, match))
                used_players.update([p['name'] for p in match])
        else:  # doubles
            match = create_doubles_match(remaining_players)
            if match:
                new_round_matches.append((court_index, match))
                used_players.update([p['name'] for p in match])
    
    return new_round_matches

@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def index():
    """Main match organizer page."""
    
    # Get current session data
    players = session.get("players", [])
    courts = session.get("courts", 1)
    num_matches = session.get("num_matches", 1)
    match_type = session.get("match_type", "singles")
    
    matchups = session.get("matchups", [])
    player_match_counts = session.get("player_match_counts", {})
    rounds = session.get("rounds", {})

    if request.method == "POST":
        # Update session configuration
        try:
            courts = int(request.form.get("courts", courts))
            num_matches = int(request.form.get("num_matches", num_matches))
        except ValueError:
            pass
        
        match_type = request.form.get("match_type", match_type)
        session.update({
            "courts": courts,
            "num_matches": num_matches,
            "match_type": match_type
        })

        # Remove player
        if "remove_player" in request.form:
            name_to_remove = request.form.get("remove_player")
            players = [p for p in players if p["name"] != name_to_remove]
            session["players"] = players
            # Clear matches when player is removed
            session.pop("matchups", None)
            session.pop("player_match_counts", None)
            session.pop("rounds", None)

        # CSV upload
        elif "upload_csv" in request.form:
            file = request.files.get("csv_file")
            if file and file.filename.endswith(".csv"):
                try:
                    content = file.read().decode("utf-8")
                    reader = csv.DictReader(io.StringIO(content))
                    
                    if reader.fieldnames and 'name' in reader.fieldnames and 'grade' in reader.fieldnames:
                        added_count = 0
                        for row in reader:
                            name = row.get("name", "").strip()
                            try:
                                grade = int(row.get("grade", "").strip())
                                if name and 1 <= grade <= 4:
                                    players.append({"name": name, "grade": grade})
                                    added_count += 1
                            except (ValueError, AttributeError):
                                continue
                        
                        if added_count > 0:
                            session["players"] = players
                            
                except (UnicodeDecodeError, Exception):
                    pass  # Silently handle errors

        # Reset everything
        elif "reset" in request.form:
            session.clear()
            return redirect("/")

        # Add individual player
        elif "add_player" in request.form:
            name = request.form.get("name", "").strip()
            try:
                grade = int(request.form.get("grade"))
            except (TypeError, ValueError):
                grade = None

            if name and grade in [1, 2, 3, 4]:
                players.append({"name": name, "grade": grade})
                session["players"] = players

        # Reshuffle specific round
        elif "reshuffle_round" in request.form:
            try:
                round_to_reshuffle = int(request.form.get("reshuffle_round"))
                
                if matchups and rounds:
                    # Generate new matches for this round
                    new_round_matches = reshuffle_single_round(
                        players, courts, match_type, round_to_reshuffle, matchups, rounds
                    )
                    
                    if new_round_matches is not None:
                        # Remove old matches for this round from all courts
                        for court_index in range(len(matchups)):
                            matchups[court_index] = [
                                (match, round_num) for match, round_num in matchups[court_index]
                                if round_num != round_to_reshuffle
                            ]
                        
                        # Add new matches
                        for court_index, match in new_round_matches:
                            if court_index < len(matchups):
                                matchups[court_index].append((match, round_to_reshuffle))
                        
                        # Rebuild rounds structure
                        round_structure = defaultdict(list)
                        for court_index, court_matches in enumerate(matchups):
                            for match, round_num in court_matches:
                                round_structure[round_num].append((court_index + 1, match))
                        rounds = dict(sorted(round_structure.items()))
                        
                        # Recalculate match counts
                        player_match_counts = {p['name']: 0 for p in players}
                        for court_matches in matchups:
                            for match, round_num in court_matches:
                                for player in match:
                                    player_match_counts[player['name']] += 1
                        
                        # Update session
                        session.update({
                            "matchups": matchups,
                            "player_match_counts": player_match_counts,
                            "rounds": rounds
                        })
                        
            except (ValueError, TypeError):
                pass  # Silently handle invalid round numbers

        # Organize matches
        elif "organize_matches" in request.form or "reshuffle" in request.form:
            if "reshuffle" in request.form:
                random.shuffle(players)

            if len(players) >= (2 if match_type == "singles" else 4):
                matchups, player_match_counts, opponent_averages, opponent_diff = organize_matches(
                    players, courts, match_type, num_matches
                )

                # Build round structure
                round_structure = defaultdict(list)
                for court_index, court_matches in enumerate(matchups):
                    for match, round_num in court_matches:
                        round_structure[round_num].append((court_index + 1, match))
                rounds = dict(sorted(round_structure.items()))

                session.update({
                    "matchups": matchups,
                    "player_match_counts": player_match_counts,
                    "rounds": rounds
                })

    return render_template(
        "index.html",
        players=players,
        matchups=matchups,
        courts=courts,
        num_matches=num_matches,
        match_type=match_type,
        player_match_counts=player_match_counts,
        rounds=rounds
    )

@app.errorhandler(404)
def not_found(error):
    return redirect("/")

@app.errorhandler(500)
def server_error(error):
    return redirect("/")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)