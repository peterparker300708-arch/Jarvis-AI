"""Flask web dashboard application for Jarvis AI."""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from utils.logger import get_logger

logger = get_logger(__name__)


def _get_system_stats() -> dict[str, Any]:
    """Collect real-time system stats via psutil."""
    try:
        import psutil  # type: ignore[import]

        cpu = psutil.cpu_percent(interval=0.1)
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot_ts = psutil.boot_time()
        uptime_seconds = int(time.time() - boot_ts)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        net = psutil.net_io_counters()
        return {
            "cpu_percent": cpu,
            "cpu_count": psutil.cpu_count(),
            "memory": {
                "total": vm.total,
                "available": vm.available,
                "used": vm.used,
                "percent": vm.percent,
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
            },
            "uptime": uptime_str,
            "uptime_seconds": uptime_seconds,
            "network": {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
            },
            "timestamp": time.time(),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("psutil unavailable: %s", exc)
        return {
            "cpu_percent": 0,
            "cpu_count": 1,
            "memory": {"total": 0, "available": 0, "used": 0, "percent": 0},
            "disk": {"total": 0, "used": 0, "free": 0, "percent": 0},
            "uptime": "N/A",
            "uptime_seconds": 0,
            "network": {"bytes_sent": 0, "bytes_recv": 0},
            "timestamp": time.time(),
        }


def _get_processes(limit: int = 20) -> list[dict[str, Any]]:
    """Return top processes sorted by CPU usage."""
    try:
        import psutil  # type: ignore[import]

        procs: list[dict[str, Any]] = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                info = p.info  # type: ignore[attr-defined]
                procs.append(
                    {
                        "pid": info.get("pid", 0),
                        "name": info.get("name", "unknown"),
                        "cpu_percent": round(info.get("cpu_percent") or 0.0, 2),
                        "memory_percent": round(info.get("memory_percent") or 0.0, 2),
                        "status": info.get("status", "unknown"),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
        return procs[:limit]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not retrieve processes: %s", exc)
        return []


def create_dashboard_app(
    jarvis_instance: Optional[Any] = None,
    secret_key: str = "jarvis-dashboard-secret",
) -> Flask:
    """Create and configure the Jarvis dashboard Flask application.

    Args:
        jarvis_instance: Optional reference to the running JarvisAI instance
            so dashboard commands can be forwarded to it.
        secret_key: Flask secret key for session management.

    Returns:
        Configured :class:`Flask` application.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = secret_key

    # ------------------------------------------------------------------
    # Main dashboard page
    # ------------------------------------------------------------------

    @app.route("/")
    def index() -> str:  # type: ignore[return]
        stats = _get_system_stats()
        return render_template("index.html", stats=stats)

    # ------------------------------------------------------------------
    # REST JSON endpoints
    # ------------------------------------------------------------------

    @app.route("/api/system")
    def api_system() -> Response:
        return jsonify(_get_system_stats())

    @app.route("/api/processes")
    def api_processes() -> Response:
        limit = min(int(request.args.get("limit", 20)), 100)
        return jsonify({"processes": _get_processes(limit), "timestamp": time.time()})

    @app.route("/api/command", methods=["POST"])
    def api_command() -> Response:
        data = request.get_json(silent=True) or {}
        command = str(data.get("command", "")).strip()
        if not command:
            return jsonify({"error": "No command provided"}), 400

        if jarvis_instance is not None:
            try:
                result = jarvis_instance.process_command(command)
                return jsonify({"command": command, "response": result, "timestamp": time.time()})
            except Exception as exc:  # noqa: BLE001
                logger.exception("Command execution error: %s", exc)
                return jsonify({"error": "Command execution failed"}), 500
        else:
            # Standalone mode: echo back with a note
            return jsonify(
                {
                    "command": command,
                    "response": f"[Dashboard standalone mode] Received: {command}",
                    "timestamp": time.time(),
                }
            )

    # ------------------------------------------------------------------
    # Server-Sent Events stream
    # ------------------------------------------------------------------

    @app.route("/api/stream")
    def api_stream() -> Response:
        """SSE endpoint that pushes system stats every 3 seconds."""

        def generate():
            while True:
                stats = _get_system_stats()
                yield f"data: {json.dumps(stats)}\n\n"
                time.sleep(3)

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    @app.route("/health")
    def health() -> Response:
        return jsonify({"status": "ok", "service": "jarvis-dashboard", "timestamp": time.time()})

    return app


def start_dashboard(
    host: str = "0.0.0.0",
    port: int = 8080,
    debug: bool = False,
    jarvis_instance: Optional[Any] = None,
    secret_key: str = "jarvis-dashboard-secret",
) -> None:
    """Start the Jarvis web dashboard server.

    Args:
        host: Network interface to bind to.
        port: TCP port to listen on.
        debug: Enable Flask debug/reload mode.
        jarvis_instance: Running JarvisAI instance (optional).
        secret_key: Flask session secret key.
    """
    app = create_dashboard_app(jarvis_instance=jarvis_instance, secret_key=secret_key)
    logger.info("Starting Jarvis dashboard on http://%s:%s", host, port)
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)


if __name__ == "__main__":
    start_dashboard(debug=True)
