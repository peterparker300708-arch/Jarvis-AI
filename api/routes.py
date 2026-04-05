"""Flask Blueprint defining all Jarvis REST API routes."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Tuple

from flask import Blueprint, jsonify, request

from database.db_manager import get_db_manager
from utils.logger import get_logger

logger = get_logger(__name__)

api_bp = Blueprint("api", __name__)

_db = None

# Allowed root for file-system API operations (restrict to user home)
_FS_ROOT = Path(os.path.expanduser("~")).resolve()


def _validate_path(path: str) -> Path:
    """Resolve *path* and ensure it does not escape the allowed filesystem root.

    Raises:
        PermissionError: If the resolved path is outside :data:`_FS_ROOT`.
    """
    resolved = Path(path).expanduser().resolve()
    try:
        resolved.relative_to(_FS_ROOT)
    except ValueError:
        raise PermissionError(
            f"Access denied: path is outside the permitted directory ({_FS_ROOT})"
        )
    return resolved


def _get_db():
    global _db
    if _db is None:
        _db = get_db_manager()
    return _db


def _ok(data: Any, status: int = 200) -> Tuple[Any, int]:
    return jsonify({"status": "success", "data": data}), status


def _err(message: str, status: int = 400) -> Tuple[Any, int]:
    return jsonify({"status": "error", "message": message}), status


# ======================================================================
# Health & Status
# ======================================================================

@api_bp.route("/api/health", methods=["GET"])
def health():
    """Lightweight health-check — no authentication required."""
    return _ok({"service": "Jarvis AI", "healthy": True, "timestamp": datetime.utcnow().isoformat()})


@api_bp.route("/api/status", methods=["GET"])
def status():
    """System resource snapshot: CPU, memory, disk."""
    try:
        from modules.system_monitor import SystemMonitor  # noqa: PLC0415
        monitor = SystemMonitor()
        snapshot = monitor.get_snapshot()
        return _ok(snapshot)
    except Exception as exc:
        logger.error("Status endpoint error: %s", exc)
        return _err("Unable to retrieve system status", 500)


# ======================================================================
# Command execution
# ======================================================================

@api_bp.route("/api/command", methods=["POST"])
def execute_command():
    """Execute a Jarvis text command.

    Body JSON: {"command": "turn on lights"}
    """
    body = request.get_json(silent=True) or {}
    command_text = body.get("command", "").strip()
    if not command_text:
        return _err("'command' field is required")

    db = _get_db()
    response_text = f"Received command: {command_text}"

    try:
        from core.ai_engine import AIEngine  # noqa: PLC0415
        engine = AIEngine()
        result = engine.process_command(command_text)
        response_text = result.get("response", str(result))
    except Exception as exc:
        logger.debug("AIEngine not available, using echo response: %s", exc)

    cmd = db.log_command(text=command_text, response=response_text, success=True)
    return _ok({"command": command_text, "response": response_text, "command_id": cmd.command_id})


# ======================================================================
# Processes
# ======================================================================

@api_bp.route("/api/processes", methods=["GET"])
def list_processes():
    """List top running processes sorted by CPU usage."""
    try:
        from modules.system_monitor import SystemMonitor  # noqa: PLC0415
        monitor = SystemMonitor()
        sort_by = request.args.get("sort_by", "cpu")
        limit = int(request.args.get("limit", 20))
        processes = monitor.get_processes(sort_by=sort_by, limit=limit)
        return _ok(processes)
    except Exception as exc:
        logger.error("list_processes error: %s", exc)
        return _err("Unable to retrieve process list", 500)
def kill_process():
    """Kill a process by PID or name.

    Body JSON: {"pid": 1234} or {"name": "firefox"}
    """
    body = request.get_json(silent=True) or {}
    pid = body.get("pid")
    name = body.get("name", "").strip()

    if not pid and not name:
        return _err("'pid' or 'name' is required")

    try:
        import psutil  # noqa: PLC0415
        killed = 0
        if pid:
            try:
                proc = psutil.Process(int(pid))
                proc.terminate()
                killed = 1
            except psutil.NoSuchProcess:
                return _err(f"No process with PID {pid}", 404)
        else:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if name.lower() in (proc.info["name"] or "").lower():
                        proc.terminate()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        if killed:
            return _ok({"killed": killed, "pid": pid, "name": name})
        return _err(f"No process found matching '{name}'", 404)
    except ImportError:
        return _err("psutil not available", 500)
    except Exception as exc:
        logger.error("kill_process error: %s", exc)
        return _err("Unable to kill process", 500)


# ======================================================================
# Files
# ======================================================================

@api_bp.route("/api/files", methods=["GET"])
def list_files():
    """List files in a directory.

    Query param: path= (defaults to user home)
    """
    raw_path = request.args.get("path", os.path.expanduser("~"))
    try:
        safe_path = _validate_path(raw_path)
        from modules.file_manager import FileManager  # noqa: PLC0415
        fm = FileManager()
        entries = fm.list_directory(str(safe_path))
        return _ok({"path": str(safe_path), "entries": entries})
    except PermissionError as exc:
        return _err(str(exc), 403)
    except FileNotFoundError:
        return _err("Directory not found", 404)
    except Exception as exc:
        logger.error("list_files error: %s", exc)
        return _err("Unable to list directory", 500)


@api_bp.route("/api/files", methods=["POST"])
def create_file_or_dir():
    """Create a file or directory.

    Body JSON: {"path": "/some/path", "type": "file"|"directory", "content": "..."}
    """
    body = request.get_json(silent=True) or {}
    raw_path = body.get("path", "")
    item_type = body.get("type", "file")
    content = body.get("content", "")

    if not raw_path:
        return _err("'path' is required")

    try:
        safe_path = _validate_path(raw_path)
        from modules.file_manager import FileManager  # noqa: PLC0415
        fm = FileManager()
        if item_type == "directory":
            result = fm.create_directory(str(safe_path))
        else:
            result = fm.create_file(str(safe_path), content)
        return _ok({"created": result, "type": item_type}, 201)
    except PermissionError as exc:
        return _err(str(exc), 403)
    except Exception as exc:
        logger.error("create_file error: %s", exc)
        return _err("Unable to create file or directory", 500)


@api_bp.route("/api/files", methods=["DELETE"])
def delete_file():
    """Delete a file or directory.

    Body JSON: {"path": "/some/path", "recycle": true}
    """
    body = request.get_json(silent=True) or {}
    raw_path = body.get("path", "")
    recycle = body.get("recycle", True)

    if not raw_path:
        return _err("'path' is required")

    try:
        safe_path = _validate_path(raw_path)
        from modules.file_manager import FileManager  # noqa: PLC0415
        fm = FileManager()
        fm.delete(str(safe_path), recycle=recycle)
        return _ok({"deleted": str(safe_path)})
    except PermissionError as exc:
        return _err(str(exc), 403)
    except FileNotFoundError:
        return _err("File not found", 404)
    except Exception as exc:
        logger.error("delete_file error: %s", exc)
        return _err("Unable to delete file", 500)


# ======================================================================
# Notes
# ======================================================================

@api_bp.route("/api/notes", methods=["GET"])
def list_notes():
    """List notes, optionally filtered by ?search=<term>."""
    search = request.args.get("search")
    notes = _get_db().get_notes(search=search)
    return _ok(notes)


@api_bp.route("/api/notes", methods=["POST"])
def create_note():
    """Create a note.

    Body JSON: {"title": "...", "content": "...", "tags": "tag1,tag2"}
    """
    body = request.get_json(silent=True) or {}
    title = body.get("title", "").strip()
    if not title:
        return _err("'title' is required")

    note = _get_db().add_note(
        title=title,
        content=body.get("content", ""),
        tags=body.get("tags", ""),
    )
    return _ok(note.to_dict(), 201)


# ======================================================================
# Reminders
# ======================================================================

@api_bp.route("/api/reminders", methods=["GET"])
def list_reminders():
    """List upcoming reminders."""
    include_done = request.args.get("include_completed", "false").lower() == "true"
    reminders = _get_db().get_all_reminders(include_completed=include_done)
    return _ok(reminders)


@api_bp.route("/api/reminders", methods=["POST"])
def create_reminder():
    """Create a reminder.

    Body JSON: {"title": "...", "message": "...", "remind_at": "2024-12-31T09:00:00"}
    """
    body = request.get_json(silent=True) or {}
    title = body.get("title", "").strip()
    message = body.get("message", "")
    remind_at_str = body.get("remind_at", "")

    if not title:
        return _err("'title' is required")
    if not remind_at_str:
        return _err("'remind_at' is required (ISO 8601 datetime string)")

    try:
        remind_at = datetime.fromisoformat(remind_at_str)
    except ValueError:
        return _err("'remind_at' must be a valid ISO 8601 datetime string")

    reminder = _get_db().add_reminder(title=title, message=message, remind_at=remind_at)
    return _ok(reminder.to_dict(), 201)


# ======================================================================
# Command history
# ======================================================================

@api_bp.route("/api/history", methods=["GET"])
def command_history():
    """Return recent command history.

    Query param: limit= (default 50)
    """
    limit = int(request.args.get("limit", 50))
    history = _get_db().get_recent_commands(limit=limit)
    return _ok(history)
