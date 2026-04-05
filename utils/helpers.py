"""Miscellaneous helper utilities for the Jarvis AI system."""

from __future__ import annotations

import os
import platform
import re
import socket
import subprocess
import sys
from typing import Tuple


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_bytes(num_bytes: int | float) -> str:
    """Convert *num_bytes* to a human-readable string (e.g. ``"3.14 MB"``).

    Args:
        num_bytes: Raw byte count.

    Returns:
        Human-readable string with appropriate unit suffix.
    """
    num_bytes = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} EB"


def format_duration(seconds: int | float) -> str:
    """Convert *seconds* to a human-readable duration string.

    Examples::

        format_duration(90)     # "1m 30s"
        format_duration(3661)   # "1h 1m 1s"
        format_duration(86400)  # "1d 0h 0m 0s"

    Args:
        seconds: Total duration in seconds.

    Returns:
        Human-readable duration string.
    """
    seconds = int(seconds)
    if seconds < 0:
        return "0s"

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Return a filesystem-safe version of *name*.

    Removes or replaces characters that are illegal on Windows/Linux/macOS.

    Args:
        name: Original filename (without path).
        replacement: Character used to replace illegal characters.

    Returns:
        Sanitized filename string.
    """
    # Remove characters illegal on Windows and/or Linux
    illegal = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(illegal, replacement, name)
    # Collapse repeated replacements
    sanitized = re.sub(rf"{re.escape(replacement)}+", replacement, sanitized)
    # Strip leading/trailing dots, spaces, and replacement chars
    sanitized = sanitized.strip(". " + replacement)
    # Truncate to 255 bytes (max filename length on most filesystems)
    sanitized = sanitized.encode("utf-8")[:255].decode("utf-8", errors="ignore")
    return sanitized or "unnamed"


# ---------------------------------------------------------------------------
# Shell command execution
# ---------------------------------------------------------------------------

def run_command(
    cmd: str | list[str],
    shell: bool = True,
    timeout: int = 30,
    cwd: str | None = None,
    env: dict | None = None,
) -> Tuple[str, str, int]:
    """Run a shell command and return ``(stdout, stderr, returncode)``.

    Args:
        cmd: Command string (when *shell* is ``True``) or list of args.
        shell: Whether to run via the system shell.
        timeout: Maximum seconds to wait before raising :exc:`TimeoutExpired`.
        cwd: Working directory for the subprocess.
        env: Optional environment variables mapping.

    Returns:
        Tuple of ``(stdout, stderr, returncode)``.
    """
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Command timed out after {timeout}s", -1
    except FileNotFoundError as exc:
        return "", str(exc), -1
    except Exception as exc:  # noqa: BLE001
        return "", str(exc), -1


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def get_platform() -> str:
    """Detect the current operating system.

    Returns:
        One of ``"windows"``, ``"linux"``, or ``"mac"``.
    """
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "mac"
    return "linux"


# ---------------------------------------------------------------------------
# Process helpers
# ---------------------------------------------------------------------------

def is_process_running(name: str) -> bool:
    """Check whether a process with the given *name* is currently running.

    Args:
        name: Process name (case-insensitive partial match).

    Returns:
        ``True`` if at least one matching process is running.
    """
    current_platform = get_platform()
    name_lower = name.lower()

    try:
        if current_platform == "windows":
            stdout, _, rc = run_command("tasklist /FO CSV /NH", shell=True, timeout=10)
            if rc != 0:
                return False
            return name_lower in stdout.lower()
        else:
            # Use pgrep when available, fall back to ps
            stdout, _, rc = run_command(f"pgrep -il {name}", shell=True, timeout=10)
            if rc == 0 and stdout:
                return True
            stdout, _, _ = run_command("ps aux", shell=True, timeout=10)
            return name_lower in stdout.lower()
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def get_ip_address() -> str:
    """Return the primary local IP address of this machine.

    Falls back to ``"127.0.0.1"`` if no network interface is available.

    Returns:
        IP address string.
    """
    try:
        # Connect to a public address without actually sending data
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        pass

    # Secondary approach: hostname resolution
    try:
        return socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        return "127.0.0.1"


# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate *text* to at most *max_length* characters.

    Args:
        text: Input string.
        max_length: Maximum character count including suffix.
        suffix: Appended when text is truncated.

    Returns:
        Possibly-truncated string.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def ensure_dir(path: str) -> str:
    """Create *path* (and any parents) if it does not already exist.

    Args:
        path: Directory path to create.

    Returns:
        The absolute path that was created or already existed.
    """
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return ``True`` if *port* on *host* is reachable within *timeout* seconds.

    Args:
        host: Hostname or IP address.
        port: TCP port number.
        timeout: Connection timeout in seconds.

    Returns:
        ``True`` if a TCP connection could be established.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False
