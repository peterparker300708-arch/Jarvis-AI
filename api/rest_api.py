"""Flask REST API factory with authentication, CORS, logging, and error handling."""

from __future__ import annotations

import logging
import time
from typing import Optional

from flask import Flask, g, jsonify, request

try:
    from flask_cors import CORS
    _CORS_AVAILABLE = True
except ImportError:
    _CORS_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)

_API_KEY_HEADER = "X-API-Key"
_DEFAULT_API_KEY = "jarvis-secret-key"


def create_app(api_key: Optional[str] = None, debug: bool = False) -> Flask:
    """Create and configure the Jarvis Flask application.

    Args:
        api_key: API key used to authenticate requests.
                 Defaults to the ``JARVIS_API_KEY`` environment variable
                 or a built-in default (for development only).
        debug: Enable Flask debug mode.

    Returns:
        Configured :class:`Flask` application instance.
    """
    import os

    app = Flask(__name__)
    app.config["DEBUG"] = debug
    app.config["JARVIS_API_KEY"] = api_key or os.environ.get("JARVIS_API_KEY", _DEFAULT_API_KEY)
    app.config["JSON_SORT_KEYS"] = False

    if _CORS_AVAILABLE:
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    else:
        logger.warning("flask-cors not installed; CORS headers will not be added.")

    # ------------------------------------------------------------------
    # Request lifecycle hooks
    # ------------------------------------------------------------------

    @app.before_request
    def _start_timer() -> None:
        g.start_time = time.time()

    @app.before_request
    def _authenticate() -> Optional[object]:
        """Enforce API key authentication for all /api/ routes."""
        if not request.path.startswith("/api/"):
            return None
        if request.path == "/api/health":
            return None
        key = (
            request.headers.get(_API_KEY_HEADER)
            or request.args.get("api_key")
            or (request.json.get("api_key") if request.is_json else None)
        )
        if key != app.config["JARVIS_API_KEY"]:
            return jsonify({"status": "error", "message": "Unauthorized — invalid or missing API key"}), 401
        return None

    @app.after_request
    def _log_request(response):
        elapsed = (time.time() - g.get("start_time", time.time())) * 1000
        logger.debug(
            "%s %s %d %.1fms",
            request.method,
            request.path,
            response.status_code,
            elapsed,
        )
        response.headers["X-Response-Time-Ms"] = f"{elapsed:.1f}"
        return response

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------

    @app.errorhandler(404)
    def _not_found(error):
        return jsonify({"status": "error", "message": "Endpoint not found", "path": request.path}), 404

    @app.errorhandler(405)
    def _method_not_allowed(error):
        return jsonify({"status": "error", "message": "Method not allowed"}), 405

    @app.errorhandler(500)
    def _internal_error(error):
        logger.error("Internal server error: %s", error)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

    @app.errorhandler(Exception)
    def _unhandled_exception(error):
        logger.exception("Unhandled exception: %s", error)
        return jsonify({"status": "error", "message": str(error)}), 500

    # ------------------------------------------------------------------
    # Register blueprints
    # ------------------------------------------------------------------

    from api.routes import api_bp  # noqa: PLC0415
    app.register_blueprint(api_bp)

    logger.info("Jarvis REST API app created (debug=%s)", debug)
    return app


def start_api(host: str = "0.0.0.0", port: int = 5000, debug: bool = False) -> None:
    """Create and start the Jarvis Flask API server.

    This is a blocking call that runs the built-in Werkzeug dev server.
    For production, use a WSGI server such as gunicorn or uWSGI.

    Args:
        host: Bind address.
        port: TCP port.
        debug: Enable Flask debug/reloader.
    """
    app = create_app(debug=debug)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logger.info("Starting Jarvis API on %s:%d (debug=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug, use_reloader=False)
