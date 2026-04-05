"""Cross-platform application launcher module."""

from __future__ import annotations

import platform
import subprocess
import shutil
from typing import Dict, List, Optional

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM = platform.system()

# Common application name -> executable/command mappings per platform
_APP_MAP_WINDOWS: Dict[str, str] = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "notepad": "notepad",
    "calculator": "calc",
    "terminal": "cmd",
    "cmd": "cmd",
    "powershell": "powershell",
    "file manager": "explorer",
    "explorer": "explorer",
    "word": "winword",
    "excel": "excel",
    "paint": "mspaint",
    "spotify": "spotify",
    "vlc": "vlc",
    "vscode": "code",
    "vs code": "code",
    "notepad++": "notepad++",
    "task manager": "taskmgr",
    "control panel": "control",
}

_APP_MAP_LINUX: Dict[str, str] = {
    "chrome": "google-chrome",
    "google chrome": "google-chrome",
    "chromium": "chromium-browser",
    "firefox": "firefox",
    "terminal": "x-terminal-emulator",
    "file manager": "nautilus",
    "nautilus": "nautilus",
    "thunar": "thunar",
    "calculator": "gnome-calculator",
    "text editor": "gedit",
    "gedit": "gedit",
    "notepad": "gedit",
    "vlc": "vlc",
    "spotify": "spotify",
    "vscode": "code",
    "vs code": "code",
    "gimp": "gimp",
    "libreoffice": "libreoffice",
    "settings": "gnome-control-center",
    "system monitor": "gnome-system-monitor",
}

_APP_MAP_MACOS: Dict[str, str] = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "firefox": "Firefox",
    "safari": "Safari",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "finder": "Finder",
    "file manager": "Finder",
    "calculator": "Calculator",
    "notes": "Notes",
    "calendar": "Calendar",
    "mail": "Mail",
    "vlc": "VLC",
    "spotify": "Spotify",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "xcode": "Xcode",
    "activity monitor": "Activity Monitor",
    "system preferences": "System Preferences",
}

_BROWSER_ALIASES = {"browser", "web browser", "internet"}


def _get_app_map() -> Dict[str, str]:
    if _SYSTEM == "Windows":
        return _APP_MAP_WINDOWS
    if _SYSTEM == "Darwin":
        return _APP_MAP_MACOS
    return _APP_MAP_LINUX


class AppLauncher:
    """Cross-platform application launcher.

    Supports launching, closing, and focusing applications by common name.
    """

    def __init__(self) -> None:
        self._app_map = _get_app_map()

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    def launch(self, app_name: str) -> Dict[str, str]:
        """Launch an application by common name.

        Args:
            app_name: Human-friendly application name (e.g. "chrome", "terminal").

        Returns:
            dict with: status ("success" or "error"), message, app_name.
        """
        name_lower = app_name.strip().lower()

        if name_lower in _BROWSER_ALIASES:
            name_lower = "browser"

        resolved = self._resolve_app_name(name_lower)
        if resolved is None:
            return {
                "status": "error",
                "message": f"Unknown application: '{app_name}'. Try providing the executable name directly.",
                "app_name": app_name,
            }

        try:
            if _SYSTEM == "Windows":
                subprocess.Popen(["start", resolved], shell=True)
            elif _SYSTEM == "Darwin":
                subprocess.Popen(["open", "-a", resolved])
            else:
                # Linux: try direct execution first, fall back to xdg-open
                if shutil.which(resolved):
                    subprocess.Popen(
                        [resolved],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    subprocess.Popen(
                        ["xdg-open", resolved],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

            logger.info("Launched application: %s (%s)", app_name, resolved)
            return {"status": "success", "message": f"Launched {app_name}", "app_name": resolved}
        except FileNotFoundError:
            return {
                "status": "error",
                "message": f"Executable not found: '{resolved}'. Is {app_name} installed?",
                "app_name": app_name,
            }
        except Exception as exc:
            logger.error("Failed to launch %s: %s", app_name, exc)
            return {"status": "error", "message": str(exc), "app_name": app_name}

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def close(self, app_name: str) -> Dict[str, str]:
        """Terminate a running application by name.

        Args:
            app_name: Name of the application (process name or common alias).

        Returns:
            dict with: status, message, killed_count.
        """
        if not _PSUTIL_AVAILABLE:
            return {"status": "error", "message": "psutil not available", "killed_count": "0"}

        resolved = self._resolve_app_name(app_name.lower()) or app_name
        killed = 0
        search_names = {app_name.lower(), resolved.lower()}

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = (proc.info["name"] or "").lower()
                if any(s in proc_name for s in search_names):
                    proc.terminate()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            logger.info("Terminated %d process(es) matching '%s'", killed, app_name)
            return {"status": "success", "message": f"Terminated {killed} process(es)", "killed_count": str(killed)}
        return {"status": "error", "message": f"No running process found for '{app_name}'", "killed_count": "0"}

    # ------------------------------------------------------------------
    # Status checks
    # ------------------------------------------------------------------

    def is_running(self, app_name: str) -> bool:
        """Return True if a process matching *app_name* is currently running."""
        if not _PSUTIL_AVAILABLE:
            return False

        resolved = self._resolve_app_name(app_name.lower()) or app_name
        search_names = {app_name.lower(), resolved.lower()}

        for proc in psutil.process_iter(["name"]):
            try:
                proc_name = (proc.info["name"] or "").lower()
                if any(s in proc_name for s in search_names):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def get_installed_apps(self) -> List[Dict[str, str]]:
        """Return a list of known/common app entries for the current platform.

        Returns:
            List of dicts with: name, executable, available (bool str).
        """
        apps: List[Dict[str, str]] = []
        for common_name, executable in self._app_map.items():
            available = "true"
            if _SYSTEM == "Linux":
                available = "true" if shutil.which(executable) else "false"
            apps.append(
                {
                    "name": common_name,
                    "executable": executable,
                    "available": available,
                    "platform": _SYSTEM,
                }
            )
        return apps

    # ------------------------------------------------------------------
    # Focus
    # ------------------------------------------------------------------

    def focus(self, app_name: str) -> Dict[str, str]:
        """Attempt to bring an application window to the foreground.

        Uses platform-specific tools. Falls back to a best-effort approach.

        Returns:
            dict with: status, message.
        """
        resolved = self._resolve_app_name(app_name.lower()) or app_name

        try:
            if _SYSTEM == "Windows":
                script = (
                    f'$wshell = New-Object -ComObject wscript.shell; '
                    f'$wshell.AppActivate("{resolved}")'
                )
                subprocess.Popen(["powershell", "-Command", script], shell=False)
                return {"status": "success", "message": f"Focused {app_name}"}

            if _SYSTEM == "Darwin":
                script = f'tell application "{resolved}" to activate'
                subprocess.Popen(["osascript", "-e", script])
                return {"status": "success", "message": f"Focused {app_name}"}

            # Linux — wmctrl is the best option
            if shutil.which("wmctrl"):
                subprocess.Popen(["wmctrl", "-a", resolved])
                return {"status": "success", "message": f"Focused {app_name}"}

            return {"status": "error", "message": "Focus not supported without wmctrl on Linux"}

        except Exception as exc:
            logger.error("Failed to focus %s: %s", app_name, exc)
            return {"status": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_app_name(self, name: str) -> Optional[str]:
        """Look up *name* in the app map, trying the default browser as a fallback."""
        if name in self._app_map:
            return self._app_map[name]
        # Try partial match
        for key, value in self._app_map.items():
            if name in key or key in name:
                return value
        # Fall back to using name as-is (might be a direct executable)
        if shutil.which(name):
            return name
        return None
