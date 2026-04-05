"""
Web Dashboard - Flask-based web UI for Jarvis AI.
"""

import json
import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

try:
    from flask import Flask, render_template, jsonify, request, redirect, url_for
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logger.warning("Flask not available — web dashboard disabled")


def create_dashboard_app(config, components: dict):
    """Create and configure the Flask web dashboard."""
    if not FLASK_AVAILABLE:
        raise ImportError("Flask is required. Install with: pip install flask flask-cors")

    app = Flask(__name__, template_folder="../web/templates", static_folder="../web/static")
    app.config["SECRET_KEY"] = config.get("web.secret_key", "dev-secret-key")
    CORS(app)

    ai = components.get("ai")
    system = components.get("system")
    memory = components.get("memory")
    db = components.get("db")
    scheduler = components.get("scheduler")
    behavior = components.get("behavior")

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        return render_template("dashboard.html")

    @app.route("/terminal")
    def terminal():
        return render_template("terminal.html")

    @app.route("/analytics")
    def analytics():
        return render_template("analytics.html")

    @app.route("/settings")
    def settings():
        prefs = db.get_all_preferences() if db else {}
        return render_template("settings.html", preferences=prefs)

    # ------------------------------------------------------------------
    # API Endpoints
    # ------------------------------------------------------------------

    @app.route("/api/status")
    def api_status():
        status = {}
        if system:
            status = system.get_system_status()
        status["ai_available"] = ai.is_available() if ai else False
        status["scheduler_running"] = scheduler.is_running() if scheduler else False
        return jsonify(status)

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        data = request.get_json()
        message = data.get("message", "")
        if not message:
            return jsonify({"error": "Empty message"}), 400
        if not ai:
            return jsonify({"error": "AI engine not initialized"}), 503
        response = ai.chat(message)
        if memory:
            memory.add("user", message)
            memory.add("assistant", response)
        if db:
            db.log_command(message, category="chat", response=response)
        return jsonify({
            "message": message,
            "response": response,
            "timestamp": datetime.now().isoformat(),
        })

    @app.route("/api/command", methods=["POST"])
    def api_command():
        data = request.get_json()
        command = data.get("command", "")
        if not command or not system:
            return jsonify({"error": "Invalid request"}), 400
        result = system.run_command(command)
        return jsonify(result)

    @app.route("/api/processes")
    def api_processes():
        if not system:
            return jsonify([])
        return jsonify(system.get_processes(top_n=20))

    @app.route("/api/history")
    def api_history():
        limit = request.args.get("limit", 50, type=int)
        if not db:
            return jsonify([])
        return jsonify(db.get_command_history(limit))

    @app.route("/api/memory")
    def api_memory():
        if not memory:
            return jsonify([])
        return jsonify(memory.get_recent(20))

    @app.route("/api/tasks")
    def api_tasks():
        if not db:
            return jsonify([])
        return jsonify(db.get_pending_tasks())

    @app.route("/api/jobs")
    def api_jobs():
        if not scheduler:
            return jsonify([])
        return jsonify(scheduler.get_jobs())

    @app.route("/api/profile")
    def api_profile():
        if not behavior:
            return jsonify({})
        return jsonify(behavior.get_behavioral_profile())

    @app.route("/api/notes")
    def api_notes():
        if not db:
            return jsonify([])
        return jsonify(db.get_notes())

    @app.route("/api/notes", methods=["POST"])
    def api_create_note():
        data = request.get_json()
        if not db or not data.get("content"):
            return jsonify({"error": "Invalid request"}), 400
        note_id = db.save_note(
            title=data.get("title", ""),
            content=data["content"],
            tags=data.get("tags", ""),
            category=data.get("category", "general"),
        )
        return jsonify({"id": note_id, "status": "created"})

    @app.route("/api/preferences", methods=["GET"])
    def api_get_preferences():
        if not db:
            return jsonify({})
        return jsonify(db.get_all_preferences())

    @app.route("/api/preferences", methods=["POST"])
    def api_set_preference():
        data = request.get_json()
        if not db or not data.get("key"):
            return jsonify({"error": "Invalid request"}), 400
        db.set_preference(data["key"], data.get("value", ""))
        return jsonify({"status": "saved"})

    return app
