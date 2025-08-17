#!/usr/bin/env python3
"""
Simple version of Tennis Match Organizer with all security disabled for debugging
"""
from dotenv import load_dotenv
load_dotenv()

import os, random, csv, io, re
from datetime import timedelta
from collections import defaultdict
from flask import Flask, render_template, request, session, redirect

from utils import organize_matches

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_key_UNSAFE_FOR_PRODUCTION")

def validate_player_name(name):
    """Simple player name validation"""
    if not name or len(name.strip()) == 0:
        return False, "Player name cannot be empty"
    
    name = name.strip()
    
    if len(name) > 50:
        return False, "Player name too long (max 50 characters)"
    
    return True, ""

@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def index():
    """Main match organizer page - simplified version."""
    
    # Debug logging
    if request.method == 'POST':
        print(f"DEBUG: POST request received")
        print(f"DEBUG: Form data: {dict(request.form)}")
    
    # Get current session data
    players = session.get("players", [])
    courts = session.get("courts", 1)
    num_matches = session.get("num_matches", 1)
    match_type = session.get("match_type", "singles")
    
    matchups = session.get("matchups", [])
    player_match_counts = session.get("player_match_counts", {})
    rounds = session.get("rounds", {})
    error = None

    if request.method == "POST":
        print("DEBUG: Processing POST request")
        
        # Update session configuration with validation
        try:
            courts_input = int(request.form.get("courts", courts))
            courts = max(1, min(20, courts_input))
            
            num_matches_input = int(request.form.get("num_matches", num_matches))
            num_matches = max(1, min(10, num_matches_input))
        except (ValueError, TypeError):
            error = "Invalid number format for courts or matches"
        
        match_type_input = request.form.get("match_type", match_type)
        if match_type_input in ["singles", "doubles"]:
            match_type = match_type_input
        
        session.update({
            "courts": courts,
            "num_matches": num_matches,
            "match_type": match_type
        })

        # Remove player
        if "remove_player" in request.form:
            name_to_remove = request.form.get("remove_player", "").strip()
            if name_to_remove:
                players = [p for p in players if p["name"] != name_to_remove]
                session["players"] = players
                session.pop("matchups", None)
                session.pop("player_match_counts", None)
                session.pop("rounds", None)
                print(f"DEBUG: Removed player: {name_to_remove}")

        # Reset everything
        elif "reset" in request.form:
            session.clear()
            print("DEBUG: Reset all data")
            return redirect("/")

        # Add individual player
        elif "add_player" in request.form:
            print("DEBUG: Processing add_player")
            name = request.form.get("name", "").strip()
            grade_str = request.form.get("grade", "")
            
            print(f"DEBUG: Name: '{name}', Grade: '{grade_str}'")
            
            # Simple validation
            is_valid_name, name_error = validate_player_name(name)
            if not is_valid_name:
                error = name_error
                print(f"DEBUG: Name validation failed: {name_error}")
            else:
                try:
                    grade = int(grade_str)
                    if not (1 <= grade <= 4):
                        error = "Grade must be between 1 and 4"
                        print(f"DEBUG: Grade out of range: {grade}")
                    elif any(p["name"].lower() == name.lower() for p in players):
                        error = f"Player '{name}' already exists"
                        print(f"DEBUG: Duplicate player: {name}")
                    elif len(players) >= 100:
                        error = "Maximum 100 players allowed"
                        print(f"DEBUG: Too many players: {len(players)}")
                    else:
                        player = {"name": name, "grade": grade}
                        players.append(player)
                        session["players"] = players
                        print(f"DEBUG: Added player: {player}")
                        return redirect("/")
                except (TypeError, ValueError):
                    error = "Invalid grade selected"
                    print(f"DEBUG: Invalid grade format: {grade_str}")

        # Organize matches
        elif "organize_matches" in request.form or "reshuffle" in request.form:
            print("DEBUG: Organizing matches")
            min_players = 2 if match_type == "singles" else 4
            
            if len(players) < min_players:
                error = f"Need at least {min_players} players for {match_type} matches"
            elif len(players) > 100:
                error = "Too many players (max 100)"
            else:
                if "reshuffle" in request.form:
                    random.shuffle(players)

                try:
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
                    print(f"DEBUG: Organized matches successfully")
                        
                except Exception as e:
                    error = "Error organizing matches. Please try again."
                    print(f"DEBUG: Error organizing matches: {e}")
    
    print(f"DEBUG: Returning template with {len(players)} players, error: {error}")
    
    return render_template(
        "index.html",
        players=players,
        matchups=matchups,
        courts=courts,
        num_matches=num_matches,
        match_type=match_type,
        player_match_counts=player_match_counts,
        rounds=rounds,
        error=error,
        csrf_available=False,
        csrf_token="",
        require_captcha=False
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)  # Use port 5001 to avoid conflicts