# admin.py
import os
import json
from flask import Blueprint, render_template, request, redirect, flash, session, abort
from flask_login import login_required, current_user
from user_utils import load_user
from datetime import datetime

# Create the blueprint first before using it
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Admin role check decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated and has admin flag
        if not current_user.is_authenticated:
            return redirect('/login')
            
        user_data = load_user(current_user.username)
        if not user_data or not user_data.get('is_admin', False):
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Load all users data
def load_all_users():
    users = []
    users_dir = "data/users"
    if os.path.exists(users_dir):
        for filename in os.listdir(users_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(users_dir, filename), 'r') as f:
                        user_data = json.load(f)
                        # Ensure we don't expose sensitive data
                        if 'password' in user_data:
                            del user_data['password']
                        if 'password_hash' in user_data:
                            del user_data['password_hash']
                        if 'password_salt' in user_data:
                            del user_data['password_salt']
                        
                        # Add registration date if missing
                        if 'registration_date' not in user_data:
                            # Use file creation date as fallback
                            file_time = os.path.getctime(os.path.join(users_dir, filename))
                            user_data['registration_date'] = datetime.fromtimestamp(file_time).strftime('%Y-%m-%d')
                            
                        users.append(user_data)
                except Exception as e:
                    print(f"Error loading user {filename}: {e}")
    return users

# Format last login timestamp into human-readable format
def format_last_login(timestamp_str):
    """Format the last login time in a human-readable format."""
    if not timestamp_str:
        return "Never"
        
    try:
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        delta = now - timestamp
        
        if delta.days == 0:
            if delta.seconds < 3600:  # Less than an hour
                minutes = delta.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:  # Less than a day
                hours = delta.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            return timestamp.strftime("%Y-%m-%d")
    except:
        return timestamp_str

# Get system metrics
def get_system_metrics():
    metrics = {
        'total_coaches': 0,
        'active_coaches': 0,  # Coaches who logged in within last 30 days
        'active_coaches_week': 0,  # Coaches who logged in within the last week
        'total_access_codes': 0,
        'total_bulletins': 0,
        'total_events': 0,
        'total_notes': 0,
        # Analytics data
        'avg_matches_per_coach': 0,
        'avg_events_per_coach': 0,
        'avg_notes_per_coach': 0,
        'avg_bulletins_per_coach': 0,
        'avg_access_codes_per_coach': 0
    }
    
    # Count coaches and active coaches
    users_dir = "data/users"
    if os.path.exists(users_dir):
        now = datetime.now()
        active_30_days = 0
        active_7_days = 0
        
        for filename in os.listdir(users_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(users_dir, filename), 'r') as f:
                        user_data = json.load(f)
                        
                    last_login = user_data.get('last_login')
                    if last_login:
                        try:
                            login_time = datetime.strptime(last_login, "%Y-%m-%d %H:%M:%S")
                            delta = now - login_time
                            
                            if delta.days <= 30:
                                active_30_days += 1
                                
                            if delta.days <= 7:
                                active_7_days += 1
                        except:
                            pass
                except:
                    pass
                    
        metrics['total_coaches'] = len([f for f in os.listdir(users_dir) if f.endswith('.json')])
        metrics['active_coaches'] = active_30_days
        metrics['active_coaches_week'] = active_7_days
    
    # Count access codes
    codes_path = "data/session_codes.json"
    if os.path.exists(codes_path):
        try:
            with open(codes_path, 'r') as f:
                codes = json.load(f)
                metrics['total_access_codes'] = len(codes)
        except:
            pass
    
    # Count bulletins, events, and notes
    bulletin_counts = []
    event_counts = []
    note_counts = []
    
    for dirname, key, counts_list in [
        ("data/bulletins", "total_bulletins", bulletin_counts),
        ("data/events", "total_events", event_counts),
        ("notes", "total_notes", note_counts)
    ]:
        if os.path.exists(dirname):
            total_count = 0
            for filename in os.listdir(dirname):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(dirname, filename), 'r') as f:
                            data = json.load(f)
                            file_count = 0
                            if isinstance(data, list):
                                file_count = len(data)
                            elif isinstance(data, dict):
                                file_count = 1
                            total_count += file_count
                            counts_list.append(file_count)
                    except:
                        pass
            metrics[key] = total_count
    
    # Calculate averages (avoid division by zero)
    coach_count = max(1, metrics['total_coaches'])
    metrics['avg_notes_per_coach'] = round(sum(note_counts) / coach_count, 1) if note_counts else 0
    metrics['avg_events_per_coach'] = round(sum(event_counts) / coach_count, 1) if event_counts else 0
    metrics['avg_bulletins_per_coach'] = round(sum(bulletin_counts) / coach_count, 1) if bulletin_counts else 0
    
    # Placeholder for matches data (would need session data tracking)
    metrics['avg_matches_per_coach'] = 5.3  # Mock value
    
    return metrics

# Admin dashboard
@admin_bp.route("/")
@login_required
@admin_required
def admin_dashboard():
    users = load_all_users()
    
    # Format the last login times
    for user in users:
        last_login = user.get("last_login")
        if last_login:
            user["last_login_formatted"] = format_last_login(last_login)
        else:
            user["last_login_formatted"] = "Never"
    
    metrics = get_system_metrics()
    return render_template("admin/dashboard.html", users=users, metrics=metrics)

# Analytics dashboard
@admin_bp.route("/analytics")
@login_required
@admin_required
def admin_analytics():
    metrics = get_system_metrics()
    
    # Get detailed coach data
    coach_data = []
    location_data = {}
    
    users_dir = "data/users"
    if os.path.exists(users_dir):
        for filename in os.listdir(users_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(users_dir, filename), 'r') as f:
                        user = json.load(f)
                        
                    username = user.get('username')
                    if not username:
                        continue
                        
                    # Count events
                    events_count = 0
                    events_path = os.path.join("data/events", f"{username}.json")
                    if os.path.exists(events_path):
                        try:
                            with open(events_path, 'r') as f:
                                events = json.load(f)
                                events_count = len(events) if isinstance(events, list) else 1
                        except:
                            pass
                    
                    # Count bulletins
                    bulletins_count = 0
                    bulletins_path = os.path.join("data/bulletins", f"{username}.json")
                    if os.path.exists(bulletins_path):
                        try:
                            with open(bulletins_path, 'r') as f:
                                bulletins = json.load(f)
                                bulletins_count = len(bulletins) if isinstance(bulletins, list) else 1
                        except:
                            pass
                    
                    # Count notes
                    notes_count = 0
                    notes_path = os.path.join("notes", f"{username}.json")
                    if os.path.exists(notes_path):
                        try:
                            with open(notes_path, 'r') as f:
                                notes = json.load(f)
                                notes_count = len(notes) if isinstance(notes, list) else 1
                        except:
                            pass
                    
                    # Count access codes
                    access_codes_count = 0
                    codes_path = "data/session_codes.json"
                    if os.path.exists(codes_path):
                        try:
                            with open(codes_path, 'r') as f:
                                codes = json.load(f)
                                access_codes_count = sum(1 for _, data in codes.items() 
                                                        if data.get('created_by') == username)
                        except:
                            pass
                    
                    # Format last login time
                    last_login = user.get('last_login')
                    if last_login:
                        last_login_formatted = format_last_login(last_login)
                    else:
                        last_login_formatted = "Never"
                    
                    # Track location
                    location = user.get('default_postcode', 'Unknown')
                    location_data[location] = location_data.get(location, 0) + 1
                    
                    # Add to coach data
                    coach_data.append({
                        'username': username,
                        'registration_date': user.get('registration_date', 'Unknown'),
                        'location': location,
                        'is_admin': user.get('is_admin', False),
                        'last_login': last_login_formatted,
                        'events': events_count,
                        'bulletins': bulletins_count,
                        'notes': notes_count,
                        'access_codes': access_codes_count
                    })
                
                except Exception as e:
                    print(f"Error processing user {filename}: {e}")
    
    # Sort coach data by username
    coach_data.sort(key=lambda x: x['username'])
    
    # Calculate average access codes per coach
    coach_count = max(1, len(coach_data))
    metrics['avg_access_codes_per_coach'] = round(sum(c['access_codes'] for c in coach_data) / coach_count, 1)
    
    # Sort location data by count (descending)
    location_data = dict(sorted(location_data.items(), key=lambda x: x[1], reverse=True))
    
    return render_template(
        "admin/analytics.html", 
        metrics=metrics, 
        coach_data=coach_data,
        location_data=location_data
    )

# Toggle admin status
@admin_bp.route("/toggle-admin/<username>", methods=["POST"])
@login_required
@admin_required
def toggle_admin(username):
    if username == current_user.username:
        flash("⚠️ You cannot remove your own admin status.", "danger")
        return redirect("/admin")
    
    user_data = load_user(username)
    if not user_data:
        flash("❌ User not found.", "danger")
        return redirect("/admin")
    
    is_admin = user_data.get('is_admin', False)
    user_data['is_admin'] = not is_admin
    
    # Save changes
    with open(os.path.join("data/users", f"{username}.json"), 'w') as f:
        json.dump(user_data, f, indent=2)
    
    action = "removed from" if is_admin else "added to"
    flash(f"✅ Admin status {action} {username}.", "success")
    return redirect("/admin")

# Delete user account (admin version)
@admin_bp.route("/delete-user/<username>", methods=["POST"])
@login_required
@admin_required
def delete_user(username):
    if username == current_user.username:
        flash("⚠️ You cannot delete your own account from here.", "danger")
        return redirect("/admin")
    
    # Get user data to check if exists
    user_data = load_user(username)
    if not user_data:
        flash("❌ User not found.", "danger")
        return redirect("/admin")
    
    # Delete user file
    try:
        os.remove(os.path.join("data/users", f"{username}.json"))
        
        # Also remove user's files
        for folder in ["notes", "data/bulletins", "data/events", "data/emails"]:
            filepath = os.path.join(folder, f"{username}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Update access codes
        codes_path = "data/session_codes.json"
        if os.path.exists(codes_path):
            with open(codes_path, 'r') as f:
                codes = json.load(f)
            # Remove codes created by this user
            codes = {k: v for k, v in codes.items() if v.get("created_by") != username}
            with open(codes_path, 'w') as f:
                json.dump(codes, f, indent=2)
                
        flash(f"✅ User '{username}' has been deleted.", "success")
    except Exception as e:
        flash(f"❌ Error deleting user: {str(e)}", "danger")
    
    return redirect("/admin")