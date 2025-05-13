# Add to blueprints/settings.py (at the top with other imports)
import os
import json
from flask import Blueprint, render_template, request, redirect, flash, session, make_response
from flask_login import login_required, current_user
from user_utils import (
    load_user, save_user, load_json_feature  # Add load_json_feature here
)
from password_utils import hash_password, verify_password

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    username = current_user.username
    session["last_form_page"] = "/settings"

    user_data = load_user(username)
    if not user_data:
        flash("⚠️ User not found.", "danger")
        return redirect("/logout")

    if request.method == "POST":
        postcode = request.form.get("postcode", "").strip()
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        
        # Handle password change if requested
        if current_password and new_password:
            # Check current password
            is_valid = False
            if "password_hash" in user_data:
                # Verify using hashed password
                is_valid = verify_password(
                    user_data["password_hash"],
                    user_data["password_salt"],
                    current_password
                )
            else:
                # Legacy plaintext password check
                is_valid = (user_data["password"] == current_password)
                
            if not is_valid:
                flash("⚠️ Current password is incorrect.", "danger")
                return redirect("/settings")
                
            # Update to new password
            hashed_password, salt = hash_password(new_password)
            user_data["password"] = new_password  # Keep for backward compatibility
            user_data["password_hash"] = hashed_password
            user_data["password_salt"] = salt
            flash("✅ Password updated successfully.", "success")

        # ✅ Update postcode
        user_data["default_postcode"] = postcode
        save_user(user_data)

        if "go_home" in request.form:
            flash("✅ Settings saved!", "success")
            return redirect("/home")

        flash("✅ Settings saved!", "success")
        return redirect("/settings")

    return render_template("settings.html", user_settings={
        "default_postcode": user_data.get("default_postcode", "")
    })


@settings_bp.route("/download-data")
@login_required
def download_data():
    username = current_user.username
    
    # Collect all user data
    user_data = load_user(username)
    
    # Remove sensitive data before export
    if user_data:
        user_data_export = user_data.copy()
        # Remove password-related fields for security
        if "password" in user_data_export:
            del user_data_export["password"]
        if "password_hash" in user_data_export:
            del user_data_export["password_hash"]
        if "password_salt" in user_data_export:
            del user_data_export["password_salt"]
    else:
        user_data_export = {}
    
    # Collect other user data
    bulletin_data = load_json_feature("data/bulletins", username)
    notes_data = load_json_feature("notes", username)
    events_data = load_json_feature("data/events", username)
    
    # Combine all data
    full_data = {
        "user_profile": user_data_export,
        "bulletins": bulletin_data,
        "notes": notes_data,
        "events": events_data
    }
    
    # Create JSON response
    response = make_response(json.dumps(full_data, indent=2))
    response.headers["Content-Disposition"] = f"attachment; filename={username}_data.json"
    response.headers["Content-Type"] = "application/json"
    
    return response