# app.py - Simplified Tennis Match Organizer
from dotenv import load_dotenv
load_dotenv()

import os, random, csv, io
from datetime import timedelta
from collections import defaultdict
from flask import Flask, render_template, request, session, redirect, flash
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

        # Handle player rounds editing
        if "edit_player_rounds" in request.form:
            player_name = request.form.get("edit_player_name")
            try:
                max_rounds = int(request.form.get("max_rounds", num_matches))
                for player in players:
                    if player["name"] == player_name:
                        if max_rounds < num_matches:
                            player["max_rounds"] = max_rounds
                        elif "max_rounds" in player:
                            del player["max_rounds"]
                        break
                session["players"] = players
            except (ValueError, TypeError):
                pass

        # Remove player
        elif "remove_player" in request.form:
            name_to_remove = request.form.get("remove_player")
            players = [p for p in players if p["name"] != name_to_remove]
            session["players"] = players

        # CSV upload
        elif "upload_csv" in request.form:
            file = request.files.get("csv_file")
            if not file or not file.filename.endswith(".csv"):
                flash("⚠️ Please upload a valid .csv file.", "warning")
            else:
                try:
                    content = file.read().decode("utf-8")
                    reader = csv.DictReader(io.StringIO(content))
                    
                    if not reader.fieldnames or 'name' not in reader.fieldnames or 'grade' not in reader.fieldnames:
                        flash("⚠️ CSV must have 'name' and 'grade' columns.", "warning")
                    else:
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
                        
                        if added_count == 0:
                            flash("⚠️ No valid players found in CSV.", "warning")
                        else:
                            session["players"] = players
                            flash(f"✅ Added {added_count} players from CSV.", "success")
                            
                except UnicodeDecodeError:
                    flash("⚠️ File encoding error. Please ensure the CSV is UTF-8 encoded.", "warning")
                except Exception as e:
                    flash(f"❌ Failed to read CSV: {str(e)}", "warning")

        # Reset everything
        elif "reset" in request.form:
            session.clear()
            flash("✅ Everything has been reset.", "success")
            return redirect("/")

        # Add individual player
        elif "add_player" in request.form:
            name = request.form.get("name", "").strip()
            try:
                grade = int(request.form.get("grade"))
            except (TypeError, ValueError):
                grade = None

            if not name or grade not in [1, 2, 3, 4]:
                flash("⚠️ Please enter a valid name and select a grade between 1-4.", "warning")
            else:
                players.append({"name": name, "grade": grade})
                session["players"] = players
                flash(f"✅ Added {name} to the session.", "success")

        # Reshuffle specific round
        elif "reshuffle_round" in request.form:
            round_to_reshuffle = int(request.form.get("reshuffle_round"))
            # Implementation for reshuffling specific round
            # (Simplified version of the complex logic from original)
            pass

        # Organize matches
        elif "organize_matches" in request.form or "reshuffle" in request.form:
            if "reshuffle" in request.form:
                random.shuffle(players)

            if len(players) < (2 if match_type == "singles" else 4):
                flash(f"⚠️ Need at least {2 if match_type == 'singles' else 4} players for {match_type}.", "warning")
            else:
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
                flash("✅ Matches organized successfully!", "success")

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
    flash("⚠️ Page not found.", "warning")
    return redirect("/")

@app.errorhandler(500)
def server_error(error):
    flash("❌ Something went wrong. Please try again.", "danger")
    return redirect("/")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)