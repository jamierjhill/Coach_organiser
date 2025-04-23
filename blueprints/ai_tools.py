import os
import json
from flask import Blueprint, render_template, request, session, jsonify, redirect, current_app
from datetime import datetime, timedelta
from openai import OpenAI

ai_tools_bp = Blueprint("ai_tools", __name__)

# === OpenAI Config ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
AI_TOOLBOX_PASSWORD = os.getenv("AI_TOOLBOX_PASSWORD")
COACHBOT_PASSWORD = os.getenv("COACHBOT_PASSWORD")
DRILL_PASSWORD = os.getenv("DRILL_PASSWORD")
SESSION_PASSWORD = os.getenv("SESSION_PASSWORD")

# === AI TOOLBOX ===
@ai_tools_bp.route("/ai-toolbox", methods=["GET", "POST"])
def ai_toolbox():
    drill = None
    session_plan = None
    chat_response = None
    error = None
    session["last_form_page"] = "/ai-toolbox"

    if not session.get("ai_toolbox_access_granted"):
        if request.method == "POST" and "password" in request.form:
            if request.form["password"] == AI_TOOLBOX_PASSWORD:
                session["ai_toolbox_access_granted"] = True
                return redirect("/ai-toolbox")
            else:
                error = "Incorrect password"
        return render_template("ai_toolbox.html", error=error)

    if request.method == "POST" and "tool" in request.form:
        tool = request.form["tool"]

        try:
            if tool == "drill":
                prompt = request.form.get("drill_prompt", "").strip()
                if prompt:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a tennis coach assistant that generates short, practical drills."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7
                    )
                    drill = response.choices[0].message.content.strip()

            elif tool == "session":
                players = request.form.get("players", "").strip()
                focus = request.form.get("focus", "").strip()
                duration = request.form.get("duration", "").strip()
                if players and focus and duration:
                    prompt = (
                        f"Create a tennis coaching session for {players} players. "
                        f"The focus is on {focus}. Duration: {duration} minutes. "
                        f"Include warm-up, main drills, and cool-down."
                    )
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a tennis coach assistant that creates practical and efficient session plans."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7
                    )
                    session_plan = response.choices[0].message.content.strip()

            elif tool == "chat":
                prompt = request.form.get("chat_prompt", "").strip()
                if prompt:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful tennis coaching assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.6
                    )
                    chat_response = response.choices[0].message.content.strip()

        except Exception as e:
            error = f"⚠️ Error: {str(e)}"

        if "go_home" in request.form:
            return redirect("/home")

    return render_template("ai_toolbox.html", drill=drill, session_plan=session_plan, chat_response=chat_response, error=error)

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

# === DRILL GENERATOR PAGE ===
@ai_tools_bp.route("/drill-generator", methods=["GET", "POST"])
def drill_generator():
    drill = None

    if not session.get("drill_access_granted"):
        if request.method == "POST":
            if request.form.get("password") == DRILL_PASSWORD:
                session["drill_access_granted"] = True
                return redirect("/drill-generator")
            return render_template("drill_generator.html", error="Incorrect password.")
        return render_template("drill_generator.html")

    if request.method == "POST" and "prompt" in request.form:
        prompt = request.form["prompt"]
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a tennis coach assistant that generates short, practical drills."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            drill = response.choices[0].message.content.strip()
        except Exception as e:
            drill = f"⚠️ Error generating drill: {str(e)}"

    return render_template("drill_generator.html", drill=drill)

@ai_tools_bp.route("/logout-drill-generator")
def logout_drill_generator():
    session.pop("drill_access_granted", None)
    return redirect("/drill-generator")

# === SESSION GENERATOR PAGE ===
@ai_tools_bp.route("/session-generator", methods=["GET", "POST"])
def session_generator():
    session_plan = None

    if not session.get("session_access_granted"):
        if request.method == "POST":
            if request.form.get("password") == SESSION_PASSWORD:
                session["session_access_granted"] = True
                return redirect("/session-generator")
            return render_template("session_generator.html", error="Incorrect password")
        return render_template("session_generator.html")

    if request.method == "POST" and "players" in request.form:
        players = request.form.get("players")
        focus = request.form.get("focus")
        duration = request.form.get("duration")

        prompt = (
            f"Create a tennis coaching session plan for {players} players. "
            f"The focus should be on {focus}, and the session should last {duration} minutes. "
            f"Include a warm-up, main drills, and a cool-down."
        )

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a tennis coach assistant that creates practical and efficient training sessions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            session_plan = response.choices[0].message.content.strip()
        except Exception as e:
            session_plan = f"⚠️ Error generating session: {str(e)}"

    return render_template("session_generator.html", session_plan=session_plan)

@ai_tools_bp.route("/logout-session-generator")
def logout_session_generator():
    session.pop("session_access_granted", None)
    return redirect("/session-generator")

# === INLINE COACHBOT PAGE ===
@ai_tools_bp.route("/coachbot", methods=["GET", "POST"])
def coachbot():
    error = None
    if not session.get("coachbot_access_granted"):
        if request.method == "POST":
            if request.form.get("password") == COACHBOT_PASSWORD:
                session["coachbot_access_granted"] = True
                return redirect("/coachbot")
            error = "Incorrect password"
        return render_template("coachbot.html", error=error)

    return render_template("coachbot.html")
