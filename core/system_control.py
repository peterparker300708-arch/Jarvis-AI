"""System control module: process management, resource info, and OS operations."""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import time
from typing import Any

from utils.helpers import get_platform, run_command
from utils.logger import get_logger

logger = get_logger(__name__)

_PLATFORM = get_platform()


# ---------------------------------------------------------------------------
# Low-level command execution
# ---------------------------------------------------------------------------

def execute_command(cmd: str, timeout: int = 30) -> dict[str, Any]:
    """Execute a shell command and return structured output.

    Args:
        cmd: Shell command string.
        timeout: Maximum seconds to wait.

    Returns:
        Dict with keys ``stdout``, ``stderr``, ``returncode``, ``success``.
    """
    stdout, stderr, rc = run_command(cmd, shell=True, timeout=timeout)
    return {
        "stdout": stdout,
        "stderr": stderr,
        "returncode": rc,
        "success": rc == 0,
    }


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

def get_running_processes() -> list[dict[str, Any]]:
    """Return a list of running processes with PID, name, and CPU/memory usage.

    Falls back to a minimal parse of ``ps`` output when psutil is unavailable.

    Returns:
        List of dicts with keys ``pid``, ``name``, ``cpu_percent``,
        ``memory_percent``, ``status``.
    """
    try:
        import psutil  # type: ignore[import]
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes
    except ImportError:
        pass

    # Fallback: parse ps output
    if _PLATFORM == "windows":
        stdout, _, _ = run_command("tasklist /FO CSV /NH")
        processes = []
        for line in stdout.splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 2:
                processes.append({"name": parts[0], "pid": _try_int(parts[1]), "cpu_percent": None, "memory_percent": None, "status": "running"})
        return processes

    stdout, _, _ = run_command("ps aux --no-headers")
    processes = []
    for line in stdout.splitlines():
        cols = line.split(None, 10)
        if len(cols) >= 11:
            processes.append({
                "pid": _try_int(cols[1]),
                "name": cols[10].split("/")[-1],
                "cpu_percent": _try_float(cols[2]),
                "memory_percent": _try_float(cols[3]),
                "status": cols[7],
            })
    return processes


def kill_process(pid_or_name: int | str) -> dict[str, Any]:
    """Kill a process by PID (int) or name (str).

    Args:
        pid_or_name: Numeric PID or process name string.

    Returns:
        Dict with ``success``, ``message`` keys.
    """
    try:
        import psutil  # type: ignore[import]
        if isinstance(pid_or_name, int) or str(pid_or_name).isdigit():
            pid = int(pid_or_name)
            p = psutil.Process(pid)
            p.terminate()
            return {"success": True, "message": f"Process {pid} terminated."}
        else:
            killed = []
            for proc in psutil.process_iter(["pid", "name"]):
                if pid_or_name.lower() in proc.info["name"].lower():
                    proc.terminate()
                    killed.append(proc.info["pid"])
            if killed:
                return {"success": True, "message": f"Terminated PIDs: {killed}"}
            return {"success": False, "message": f"No process matching '{pid_or_name}' found."}
    except ImportError:
        pass

    # Fallback
    if _PLATFORM == "windows":
        if isinstance(pid_or_name, int) or str(pid_or_name).isdigit():
            cmd = f"taskkill /PID {pid_or_name} /F"
        else:
            cmd = f"taskkill /IM {pid_or_name} /F"
    else:
        if isinstance(pid_or_name, int) or str(pid_or_name).isdigit():
            cmd = f"kill -9 {pid_or_name}"
        else:
            cmd = f"pkill -f {pid_or_name}"

    _, stderr, rc = run_command(cmd)
    return {
        "success": rc == 0,
        "message": f"Killed {pid_or_name}" if rc == 0 else stderr,
    }


def start_process(cmd: str) -> dict[str, Any]:
    """Start a new detached process.

    Args:
        cmd: Command string to execute.

    Returns:
        Dict with ``success``, ``pid``, and ``message`` keys.
    """
    try:
        if _PLATFORM == "windows":
            proc = subprocess.Popen(
                cmd,
                shell=True,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return {"success": True, "pid": proc.pid, "message": f"Process started with PID {proc.pid}."}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "pid": None, "message": str(exc)}


# ---------------------------------------------------------------------------
# System information
# ---------------------------------------------------------------------------

def get_system_info() -> dict[str, Any]:
    """Return a high-level overview of system resource usage.

    Returns:
        Dict with ``cpu_percent``, ``memory_percent``, ``disk_percent``,
        ``uptime``, ``hostname``, ``platform``, and ``python_version``.
    """
    info: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
        "uptime": None,
    }

    try:
        import psutil  # type: ignore[import]
        info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        info["memory_percent"] = mem.percent
        disk = psutil.disk_usage("/")
        info["disk_percent"] = disk.percent
        info["uptime"] = int(time.time() - psutil.boot_time())
    except ImportError:
        # Minimal fallback via shell commands
        if _PLATFORM == "linux":
            stdout, _, _ = run_command("cat /proc/uptime")
            if stdout:
                info["uptime"] = int(float(stdout.split()[0]))
    return info


def get_cpu_info() -> dict[str, Any]:
    """Return detailed CPU information.

    Returns:
        Dict with ``physical_cores``, ``logical_cores``, ``current_freq_mhz``,
        ``cpu_percent_per_core``, and ``model``.
    """
    info: dict[str, Any] = {
        "model": platform.processor() or "Unknown",
        "physical_cores": None,
        "logical_cores": None,
        "current_freq_mhz": None,
        "cpu_percent": None,
        "cpu_percent_per_core": [],
    }
    try:
        import psutil  # type: ignore[import]
        info["physical_cores"] = psutil.cpu_count(logical=False)
        info["logical_cores"] = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        if freq:
            info["current_freq_mhz"] = round(freq.current, 2)
        info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        info["cpu_percent_per_core"] = psutil.cpu_percent(interval=0.1, percpu=True)
    except ImportError:
        pass
    return info


def get_memory_info() -> dict[str, Any]:
    """Return virtual and swap memory statistics.

    Returns:
        Dict with ``total``, ``available``, ``used``, ``percent``,
        ``swap_total``, ``swap_used``, ``swap_percent`` (all in bytes).
    """
    info: dict[str, Any] = {
        "total": None,
        "available": None,
        "used": None,
        "percent": None,
        "swap_total": None,
        "swap_used": None,
        "swap_percent": None,
    }
    try:
        import psutil  # type: ignore[import]
        mem = psutil.virtual_memory()
        info.update({
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
        })
        swap = psutil.swap_memory()
        info.update({
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
        })
    except ImportError:
        if _PLATFORM == "linux":
            stdout, _, _ = run_command("free -b")
            lines = stdout.splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 3:
                    info["total"] = _try_int(parts[1])
                    info["used"] = _try_int(parts[2])
                    available_val = _try_int(parts[3]) if len(parts) > 3 else None
                    info["available"] = available_val
                    if info["total"] and info["used"]:
                        info["percent"] = round(info["used"] / info["total"] * 100, 1)
    return info


def get_disk_info() -> list[dict[str, Any]]:
    """Return disk usage for all mounted partitions.

    Returns:
        List of dicts with ``device``, ``mountpoint``, ``fstype``,
        ``total``, ``used``, ``free``, ``percent``.
    """
    partitions = []
    try:
        import psutil  # type: ignore[import]
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                })
            except PermissionError:
                continue
    except ImportError:
        # Fallback: df
        stdout, _, rc = run_command("df -B1 --output=source,target,fstype,size,used,avail,pcent")
        if rc == 0:
            for line in stdout.splitlines()[1:]:
                cols = line.split()
                if len(cols) >= 7:
                    partitions.append({
                        "device": cols[0],
                        "mountpoint": cols[1],
                        "fstype": cols[2],
                        "total": _try_int(cols[3]),
                        "used": _try_int(cols[4]),
                        "free": _try_int(cols[5]),
                        "percent": _try_float(cols[6].rstrip("%")),
                    })
    return partitions


def get_network_info() -> dict[str, Any]:
    """Return network interface addresses and I/O counters.

    Returns:
        Dict with ``interfaces`` (address list) and ``io_counters``
        (bytes sent/received per interface).
    """
    info: dict[str, Any] = {"interfaces": {}, "io_counters": {}}
    try:
        import psutil  # type: ignore[import]
        addrs = psutil.net_if_addrs()
        for iface, addr_list in addrs.items():
            info["interfaces"][iface] = [
                {"family": str(a.family), "address": a.address, "netmask": a.netmask}
                for a in addr_list
            ]
        counters = psutil.net_io_counters(pernic=True)
        for iface, cnt in counters.items():
            info["io_counters"][iface] = {
                "bytes_sent": cnt.bytes_sent,
                "bytes_recv": cnt.bytes_recv,
                "packets_sent": cnt.packets_sent,
                "packets_recv": cnt.packets_recv,
            }
    except ImportError:
        # Minimal fallback: ip addr
        stdout, _, _ = run_command("ip addr 2>/dev/null || ifconfig 2>/dev/null")
        info["raw"] = stdout
    return info


# ---------------------------------------------------------------------------
# Volume control
# ---------------------------------------------------------------------------

def get_volume() -> int:
    """Get the current system master volume level (0–100).

    Returns:
        Volume percentage as integer, or -1 if unavailable.
    """
    try:
        if _PLATFORM == "linux":
            stdout, _, rc = run_command("amixer get Master 2>/dev/null")
            if rc == 0:
                import re
                match = re.search(r"\[(\d+)%\]", stdout)
                if match:
                    return int(match.group(1))
        elif _PLATFORM == "mac":
            stdout, _, rc = run_command("osascript -e 'output volume of (get volume settings)'")
            if rc == 0:
                return int(stdout.strip())
        elif _PLATFORM == "windows":
            # Requires nircmd or pycaw
            pass
    except Exception:  # noqa: BLE001
        pass
    return -1


def set_volume(level: int) -> dict[str, Any]:
    """Set the system master volume to *level* percent.

    Args:
        level: Volume level 0–100.

    Returns:
        Dict with ``success`` and ``message`` keys.
    """
    level = max(0, min(100, level))
    try:
        if _PLATFORM == "linux":
            _, stderr, rc = run_command(f"amixer set Master {level}% 2>&1")
            return {"success": rc == 0, "message": f"Volume set to {level}%" if rc == 0 else stderr}
        elif _PLATFORM == "mac":
            _, stderr, rc = run_command(f"osascript -e 'set volume output volume {level}'")
            return {"success": rc == 0, "message": f"Volume set to {level}%" if rc == 0 else stderr}
        elif _PLATFORM == "windows":
            # nircmd approach
            _, stderr, rc = run_command(f"nircmd.exe setsysvolume {int(level * 655.35)}")
            return {"success": rc == 0, "message": f"Volume set to {level}%" if rc == 0 else stderr}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": str(exc)}
    return {"success": False, "message": "Volume control not supported on this platform."}


# ---------------------------------------------------------------------------
# Screen / power management
# ---------------------------------------------------------------------------

def lock_screen() -> dict[str, Any]:
    """Lock the current user session.

    Returns:
        Dict with ``success`` and ``message`` keys.
    """
    if _PLATFORM == "linux":
        for cmd in ("gnome-screensaver-command -l", "xdg-screensaver lock", "loginctl lock-session"):
            _, _, rc = run_command(cmd)
            if rc == 0:
                return {"success": True, "message": "Screen locked."}
    elif _PLATFORM == "mac":
        _, _, rc = run_command("pmset displaysleepnow")
        return {"success": rc == 0, "message": "Screen locked." if rc == 0 else "Could not lock screen."}
    elif _PLATFORM == "windows":
        _, _, rc = run_command("rundll32.exe user32.dll,LockWorkStation")
        return {"success": rc == 0, "message": "Screen locked." if rc == 0 else "Could not lock screen."}
    return {"success": False, "message": "Screen lock not supported on this platform."}


def shutdown(delay: int = 0) -> dict[str, Any]:
    """Initiate a system shutdown.

    Args:
        delay: Seconds to wait before shutting down.

    Returns:
        Dict with ``success`` and ``message`` keys.
    """
    if _PLATFORM == "linux":
        cmd = f"shutdown -h +{delay // 60}" if delay else "shutdown -h now"
    elif _PLATFORM == "mac":
        cmd = f"shutdown -h +{delay // 60}" if delay else "shutdown -h now"
    elif _PLATFORM == "windows":
        cmd = f"shutdown /s /t {delay}"
    else:
        return {"success": False, "message": "Shutdown not supported."}
    _, stderr, rc = run_command(cmd)
    return {"success": rc == 0, "message": "Shutdown initiated." if rc == 0 else stderr}


def restart(delay: int = 0) -> dict[str, Any]:
    """Initiate a system restart.

    Args:
        delay: Seconds to wait before restarting.

    Returns:
        Dict with ``success`` and ``message`` keys.
    """
    if _PLATFORM == "linux":
        cmd = f"shutdown -r +{delay // 60}" if delay else "shutdown -r now"
    elif _PLATFORM == "mac":
        cmd = f"shutdown -r +{delay // 60}" if delay else "shutdown -r now"
    elif _PLATFORM == "windows":
        cmd = f"shutdown /r /t {delay}"
    else:
        return {"success": False, "message": "Restart not supported."}
    _, stderr, rc = run_command(cmd)
    return {"success": rc == 0, "message": "Restart initiated." if rc == 0 else stderr}


def sleep_system() -> dict[str, Any]:
    """Put the system into sleep/suspend mode.

    Returns:
        Dict with ``success`` and ``message`` keys.
    """
    if _PLATFORM == "linux":
        cmd = "systemctl suspend"
    elif _PLATFORM == "mac":
        cmd = "pmset sleepnow"
    elif _PLATFORM == "windows":
        cmd = "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"
    else:
        return {"success": False, "message": "Sleep not supported."}
    _, stderr, rc = run_command(cmd)
    return {"success": rc == 0, "message": "System sleeping." if rc == 0 else stderr}


# ---------------------------------------------------------------------------
# File & environment
# ---------------------------------------------------------------------------

def open_file(path: str) -> dict[str, Any]:
    """Open *path* with the default application.

    Args:
        path: Filesystem path to open.

    Returns:
        Dict with ``success`` and ``message`` keys.
    """
    if not os.path.exists(path):
        return {"success": False, "message": f"Path does not exist: {path}"}

    try:
        if _PLATFORM == "linux":
            subprocess.Popen(["xdg-open", path], start_new_session=True)
        elif _PLATFORM == "mac":
            subprocess.Popen(["open", path], start_new_session=True)
        elif _PLATFORM == "windows":
            os.startfile(path)  # type: ignore[attr-defined]
        return {"success": True, "message": f"Opened: {path}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": str(exc)}


def get_environment_vars() -> dict[str, str]:
    """Return a copy of the current process environment variables.

    Returns:
        Dict mapping variable names to their string values.
    """
    return dict(os.environ)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _try_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _try_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
