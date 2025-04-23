import os, json
from flask import Blueprint, render_template, request, redirect, flash, session
from flask_login import login_required, current_user
from user_utils import (
    load_user, save_user, rename_user_file,
    rename_feature_file, user_path
)

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    old_username = current_user.username
    session["last_form_page"] = "/settings"

    user_data = load_user(old_username)
    if not user_data:
        flash("⚠️ User not found.", "danger")
        return redirect("/logout")

    if request.method == "POST":
        postcode = request.form.get("postcode", "").strip()
        new_username = request.form.get("new_username", "").strip()

        # ✅ Handle username change
        if new_username and new_username != old_username:
            new_path = user_path(new_username)

            # Prevent renaming to an already-existing user
            if os.path.exists(new_path) and new_username != user_data.get("username"):
                flash("⚠️ That username already exists.", "danger")
                return redirect("/settings")

            # Update and save user file
            user_data["username"] = new_username
            user_data["default_postcode"] = postcode
            rename_user_file(old_username, new_username)
            save_user(user_data)

            # Rename associated data files
            rename_feature_file("notes", old_username, new_username)
            rename_feature_file("data/bulletins", old_username, new_username)
            rename_feature_file("data/events", old_username, new_username)
            rename_feature_file("data/emails", old_username, new_username)

            # Update access code ownership
            codes_path = "data/session_codes.json"
            if os.path.exists(codes_path):
                with open(codes_path, "r") as f:
                    codes = json.load(f)
                for code, data in codes.items():
                    if data.get("created_by") == old_username:
                        data["created_by"] = new_username
                with open(codes_path, "w") as f:
                    json.dump(codes, f, indent=2)

            # ✅ Rename email subscription file if it exists
            old_email_file = f"data/emails/{old_username}.json"
            new_email_file = f"data/emails/{new_username}.json"
            if os.path.exists(old_email_file):
                os.rename(old_email_file, new_email_file)

            flash("✅ Username changed. Please log in again.", "success")
            return redirect("/logout")

        # ✅ Just update postcode
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
