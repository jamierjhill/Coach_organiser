import os
import json
from flask import Blueprint, render_template, request, redirect, flash, session, abort
from flask_login import login_required, current_user
from user_utils import load_user
from datetime import datetime

admin_bp = Blueprint("admin", __name__)

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

# Get system metrics
def get_system_metrics():
    metrics = {
        'total_coaches': 0,
        'active_coaches': 0,  # Coaches who logged in within last 30 days
        'total_access_codes': 0,
        'total_bulletins': 0,
        'total_events': 0,
        'total_notes': 0
    }
    
    # Count coaches
    users_dir = "data/users"
    if os.path.exists(users_dir):
        metrics['total_coaches'] = len([f for f in os.listdir(users_dir) if f.endswith('.json')])
    
    # Count active coaches (placeholder - would need login tracking)
    metrics['active_coaches'] = metrics['total_coaches']  # For now, assume all are active
    
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
    for dirname, key in [
        ("data/bulletins", "total_bulletins"),
        ("data/events", "total_events"),
        ("notes", "total_notes")
    ]:
        if os.path.exists(dirname):
            count = 0
            for filename in os.listdir(dirname):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(dirname, filename), 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                count += len(data)
                            elif isinstance(data, dict):
                                count += 1
                    except:
                        pass
            metrics[key] = count
    
    return metrics

# Admin dashboard
@admin_bp.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    users = load_all_users()
    metrics = get_system_metrics()
    return render_template("admin/dashboard.html", users=users, metrics=metrics)

# Toggle admin status
@admin_bp.route("/admin/toggle-admin/<username>", methods=["POST"])
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
@admin_bp.route("/admin/delete-user/<username>", methods=["POST"])
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