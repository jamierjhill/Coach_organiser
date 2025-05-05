from middleware import with_valid_session, admin_required

# In your blueprints, you can use them like:
@route_bp.route("/some-protected-route")
@with_valid_session
def protected_route():
    # This function will only run if the session is valid
    return render_template("protected_page.html")

@admin_bp.route("/admin-only-feature")
@admin_required
def admin_feature():
    # This function will only run for admin users
    return render_template("admin_feature.html")