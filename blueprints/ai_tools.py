import os
import json
from flask import Blueprint, render_template, request, session, jsonify, redirect, current_app
from datetime import datetime, timedelta
from openai import OpenAI

ai_tools_bp = Blueprint("ai_tools", __name__)

# === OpenAI Config ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
COACHBOT_PASSWORD = os.getenv("COACHBOT_PASSWORD")

# === AI TOOLBOX ===
@ai_tools_bp.route("/ai-toolbox", methods=["GET"])
def ai_toolbox():
    """
    Render the simplified CoachBot interface.
    No longer processes session or drill generation.
    """
    session["last_form_page"] = "/ai-toolbox"
    
    # Direct access without password
    session["ai_toolbox_access_granted"] = True
    
    return render_template("ai_toolbox.html")

# === COACHBOT AJAX ===
@ai_tools_bp.route("/chatbot", methods=["POST"])
def chatbot():
    try:
        user_input = request.json.get("message", "")
        if not user_input:
            return jsonify({"success": False, "error": "❌ No message received."})

        now = datetime.now()
        session.setdefault("chatbot_calls", [])

        # Clean old calls
        session["chatbot_calls"] = [
            t for t in session["chatbot_calls"]
            if datetime.fromisoformat(t) > now - timedelta(hours=1)
        ]

        if len(session["chatbot_calls"]) >= 10:
            return jsonify({"success": False, "error": "⏳ Limit reached: 10 messages/hour."})

        session["chatbot_calls"].append(now.isoformat())
        session.modified = True

        # Moderation
        moderation = client.moderations.create(input=user_input)
        if moderation.results[0].flagged:
            return jsonify({"success": False, "error": "🚫 Please ask tennis-related questions only."})

        # First time system prompt
        if "chatbot_history" not in session:
            session["chatbot_history"] = [{
                "role": "system",
                "content": (
                    "You are a level 4 LTA tennis coaching assistant. "
                    "Only answer tennis questions. Keep answers short. Suggest drills or tips."
                )
            }]

        session["chatbot_history"].append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=session["chatbot_history"],
            temperature=0.6
        )

        reply = response.choices[0].message.content.strip()
        session["chatbot_history"].append({"role": "assistant", "content": reply})
        session.modified = True

        return jsonify({"success": True, "reply": reply})

    except Exception as e:
        return jsonify({"success": False, "error": f"⚠️ An error occurred: {str(e)}"})

# === INLINE COACHBOT PAGE ===
@ai_tools_bp.route("/coachbot", methods=["GET"])
def coachbot():
    # No longer checking for password - direct access
    session["coachbot_access_granted"] = True
    return render_template("coachbot.html")