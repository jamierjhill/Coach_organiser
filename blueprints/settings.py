# blueprints/settings.py
import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, flash, session, make_response, jsonify
from flask_login import login_required, current_user
from user_utils import (
    load_user, save_user, load_json_feature, feature_path
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
        # Handle postcode update
        postcode = request.form.get("postcode", "").strip()
        user_data["default_postcode"] = postcode
        
        # Handle password change if requested
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        
        if current_password and new_password:
            # Verify current password
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

        # Handle cookie consent update
        cookie_consent = request.form.get("cookie_consent")
        if cookie_consent in ["essential", "all"]:
            # Record the previous consent value for audit
            previous_consent = user_data.get("cookie_consent", "essential")
            
            # Update consent value
            user_data["cookie_consent"] = cookie_consent
            
            # Initialize consent records if not present
            if "consent_records" not in user_data:
                user_data["consent_records"] = []
                
            # Add consent record
            user_data["consent_records"].append({
                "timestamp": datetime.now().isoformat(),
                "action": "update",
                "previous_level": previous_consent,
                "current_level": cookie_consent,
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", "Unknown")
            })
            
            # Set cookie for client-side consent management
            resp = make_response(redirect("/settings"))
            resp.set_cookie(
                "cookie_consent", 
                cookie_consent, 
                max_age=365*24*60*60, 
                samesite="Lax",
                secure=request.is_secure
            )
            resp.set_cookie(
                "consent_timestamp", 
                datetime.now().isoformat(), 
                max_age=365*24*60*60,
                samesite="Lax",
                secure=request.is_secure
            )
            
            flash("✅ Privacy preferences updated.", "success")
            save_user(user_data)
            return resp

        # Save updated user data
        save_user(user_data)

        if "go_home" in request.form:
            flash("✅ Settings saved!", "success")
            return redirect("/home")

        flash("✅ Settings saved!", "success")
        return redirect("/settings")

    # Get the user's current consent setting
    cookie_consent = user_data.get("cookie_consent", "essential")
    
    # Get consent history for display
    consent_history = user_data.get("consent_records", [])
    
    return render_template("settings.html", user_settings={
        "default_postcode": user_data.get("default_postcode", ""),
        "cookie_consent": cookie_consent,
        "consent_history": consent_history
    })

@settings_bp.route("/record-consent", methods=["POST"])
@login_required
def record_consent():
    """Record user's consent preferences via AJAX"""
    try:
        data = request.get_json()
        consent_level = data.get("level")
        
        if consent_level not in ["essential", "all"]:
            return jsonify({"success": False, "error": "Invalid consent level"}), 400
            
        username = current_user.username
        user_data = load_user(username)
        
        if not user_data:
            return jsonify({"success": False, "error": "User not found"}), 404
            
        # Record previous consent for audit
        previous_consent = user_data.get("cookie_consent", "essential")
        
        # Update user's consent level
        user_data["cookie_consent"] = consent_level
        
        # Initialize consent records if not present
        if "consent_records" not in user_data:
            user_data["consent_records"] = []
            
        # Add new consent record
        user_data["consent_records"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "update_via_ajax",
            "previous_level": previous_consent,
            "current_level": consent_level,
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "Unknown")
        })
        
        # Save updated user data
        save_user(user_data)
        
        # Set cookies for client-side consent management
        resp = jsonify({"success": True})
        resp.set_cookie(
            "cookie_consent", 
            consent_level, 
            max_age=365*24*60*60, 
            samesite="Lax",
            secure=request.is_secure
        )
        resp.set_cookie(
            "consent_timestamp", 
            datetime.now().isoformat(), 
            max_age=365*24*60*60,
            samesite="Lax",
            secure=request.is_secure
        )
        
        return resp
        
    except Exception as e:
        print(f"Error recording consent: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route("/download-data")
@login_required
def download_data():
    """Allow users to download all their personal data"""
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
    response.headers["Content-Disposition"] = f"attachment; filename={username}_data_{datetime.now().strftime('%Y%m%d')}.json"
    response.headers["Content-Type"] = "application/json"
    
    # Record data export in user profile
    if user_data:
        if "data_exports" not in user_data:
            user_data["data_exports"] = []
            
        user_data["data_exports"].append({
            "timestamp": datetime.now().isoformat(),
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "Unknown")
        })
        
        save_user(user_data)
    
    return response

@settings_bp.route("/privacy-preferences")
@login_required
def privacy_preferences():
    """Dedicated page for privacy settings"""
    username = current_user.username
    user_data = load_user(username)
    
    if not user_data:
        flash("⚠️ User not found.", "danger")
        return redirect("/logout")
        
    cookie_consent = user_data.get("cookie_consent", "essential")
    consent_history = user_data.get("consent_records", [])
    data_exports = user_data.get("data_exports", [])
    
    return render_template("privacy_preferences.html", 
        cookie_consent=cookie_consent,
        consent_history=consent_history,
        data_exports=data_exports
    )