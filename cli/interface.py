"""Jarvis AI – Interactive CLI interface using Python's cmd module."""

from __future__ import annotations

import cmd
import os
import readline  # noqa: F401  – imported for side-effect (tab completion on Linux/macOS)
import shlex
import sys
import textwrap
from datetime import datetime
from typing import Any, Optional

# ---------------------------------------------------------------------------
# ANSI colour helpers (cross-platform via colorama if available)
# ---------------------------------------------------------------------------
try:
    import colorama  # type: ignore[import]
    colorama.init(autoreset=True)
    _COLORAMA = True
except ImportError:
    _COLORAMA = False


class _C:
    """ANSI escape codes."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    CYAN    = "\033[96m"
    BLUE    = "\033[34m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    GREY    = "\033[90m"


def _c(text: str, *codes: str) -> str:
    """Wrap *text* with ANSI *codes* when stdout is a TTY."""
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + text + _C.RESET


# ---------------------------------------------------------------------------
# ASCII banner
# ---------------------------------------------------------------------------

_BANNER = r"""
  ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
  ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
  ██║███████║██████╔╝██║   ██║██║███████╗
  ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║
  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""

_INTRO_LINES = [
    _c(_BANNER, _C.CYAN, _C.BOLD),
    _c("  AI Control System  v1.0.0", _C.BLUE),
    _c("  Type 'help' for available commands. Type 'exit' to quit.", _C.GREY),
    _c("  " + "─" * 52, _C.GREY),
    "",
]

INTRO = "\n".join(_INTRO_LINES)


# ---------------------------------------------------------------------------
# Helper: pretty-print a table
# ---------------------------------------------------------------------------

def _table(headers: list[str], rows: list[list[Any]], col_widths: Optional[list[int]] = None) -> None:
    if col_widths is None:
        col_widths = [
            max(len(str(headers[i])), *(len(str(r[i])) for r in rows) if rows else (0,))
            for i in range(len(headers))
        ]
    sep = _c("  ".join("─" * w for w in col_widths), _C.GREY)
    header_row = "  ".join(
        _c(str(h).ljust(w), _C.CYAN, _C.BOLD)
        for h, w in zip(headers, col_widths)
    )
    print(sep)
    print(header_row)
    print(sep)
    for row in rows:
        print("  ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths)))
    print(sep)


# ---------------------------------------------------------------------------
# JarvisCLI
# ---------------------------------------------------------------------------

class JarvisCLI(cmd.Cmd):
    """Interactive command-line interface for Jarvis AI.

    Args:
        jarvis_instance: Optional running :class:`JarvisAI` instance; if
            provided, commands are forwarded to its ``process_command`` method.
    """

    intro: str = INTRO
    prompt: str = _c("JARVIS> ", _C.CYAN, _C.BOLD)

    def __init__(self, jarvis_instance: Optional[Any] = None) -> None:
        super().__init__()
        self._jarvis = jarvis_instance
        self._history: list[str] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _info(self, msg: str) -> None:
        print(_c("  ✓ ", _C.GREEN) + msg)

    def _warn(self, msg: str) -> None:
        print(_c("  ⚠ ", _C.YELLOW) + msg)

    def _error(self, msg: str) -> None:
        print(_c("  ✗ ", _C.RED) + msg)

    def _header(self, title: str) -> None:
        print()
        print(_c(f"  ┌─ {title} ", _C.CYAN) + _c("─" * max(0, 50 - len(title)), _C.GREY))

    def _forward(self, text: str) -> str | None:
        """Forward a command to the JarvisAI instance if available."""
        if self._jarvis is not None:
            try:
                return self._jarvis.process_command(text)
            except Exception as exc:  # noqa: BLE001
                self._error(str(exc))
        return None

    def _record(self, line: str) -> None:
        self._history.append(line)

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def default(self, line: str) -> None:
        """Forward unrecognised commands to the AI engine as a chat message."""
        self._record(line)
        result = self._forward(line)
        if result:
            print(_c("  Jarvis: ", _C.MAGENTA) + result)
        else:
            self._warn(f"Unknown command: '{line}'.  Type 'help' for available commands.")

    def emptyline(self) -> None:
        """Do nothing on empty input (suppress default repeat-last-command)."""

    def postcmd(self, stop: bool, line: str) -> bool:
        print()  # blank line between commands for readability
        return stop

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------

    def do_status(self, _arg: str) -> None:
        """Show current system status (CPU, memory, disk, uptime)."""
        self._record("status")
        self._header("SYSTEM STATUS")
        try:
            import psutil  # type: ignore[import]
            import time

            cpu = psutil.cpu_percent(interval=0.3)
            vm  = psutil.virtual_memory()
            dk  = psutil.disk_usage("/")
            up  = int(time.time() - psutil.boot_time())
            h, r = divmod(up, 3600)
            m, s = divmod(r, 60)

            def bar(pct: float, width: int = 20) -> str:
                filled = int(width * pct / 100)
                colour = _C.GREEN if pct < 60 else (_C.YELLOW if pct < 85 else _C.RED)
                return _c("█" * filled, colour) + _c("░" * (width - filled), _C.GREY)

            rows = [
                ["CPU",    f"{cpu:5.1f}%", bar(cpu)],
                ["Memory", f"{vm.percent:5.1f}%", bar(vm.percent)],
                ["Disk",   f"{dk.percent:5.1f}%", bar(dk.percent)],
            ]
            print()
            for label, pct_str, b in rows:
                print(f"  {_c(label.ljust(8), _C.CYAN)} {pct_str}  {b}")
            print()
            print(f"  {_c('Uptime:', _C.CYAN)} {h}h {m}m {s}s")
            print(f"  {_c('RAM:   ', _C.CYAN)} {vm.used // 1024**2} MB used / "
                  f"{vm.total // 1024**2} MB total")
            print(f"  {_c('Disk:  ', _C.CYAN)} {dk.used // 1024**3:.1f} GB used / "
                  f"{dk.total // 1024**3:.1f} GB total")
        except ImportError:
            result = self._forward("system status")
            if result:
                print(textwrap.indent(result, "  "))
            else:
                self._warn("psutil not installed – cannot retrieve system stats.")

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def do_execute(self, arg: str) -> None:
        """Execute a shell command.\n  Usage: execute <command>"""
        self._record(f"execute {arg}")
        if not arg.strip():
            self._error("No command provided.")
            return
        self._header(f"EXECUTE: {arg}")
        from core.system_control import execute_command  # type: ignore[import]
        result = execute_command(arg)
        if result["stdout"]:
            print(textwrap.indent(result["stdout"], "  "))
        if result["stderr"]:
            print(_c(textwrap.indent(result["stderr"], "  "), _C.YELLOW))
        status = _c("OK", _C.GREEN) if result["success"] else _c("FAILED", _C.RED)
        print(f"  Exit code: {result['returncode']}  [{status}]")

    # ------------------------------------------------------------------
    # files
    # ------------------------------------------------------------------

    def do_files(self, arg: str) -> None:
        """List files in a directory.\n  Usage: files [path]"""
        self._record(f"files {arg}")
        path = arg.strip() or "."
        self._header(f"FILES: {os.path.abspath(path)}")
        try:
            entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
            rows = []
            for entry in entries:
                try:
                    stat = entry.stat()
                    size = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    kind = "DIR " if entry.is_dir() else "FILE"
                    rows.append([kind, entry.name, str(size), mtime])
                except OSError:
                    rows.append(["?", entry.name, "–", "–"])
            if rows:
                _table(["Type", "Name", "Size", "Modified"], rows, [5, 36, 12, 17])
            else:
                self._info("Directory is empty.")
        except FileNotFoundError:
            self._error(f"Path not found: {path}")
        except PermissionError:
            self._error(f"Permission denied: {path}")

    # ------------------------------------------------------------------
    # processes
    # ------------------------------------------------------------------

    def do_processes(self, _arg: str) -> None:
        """List top running processes by CPU usage."""
        self._record("processes")
        self._header("TOP PROCESSES")
        try:
            import psutil  # type: ignore[import]
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
                try:
                    info = p.info  # type: ignore[attr-defined]
                    procs.append([
                        str(info.get("pid", "")),
                        (info.get("name") or "")[:28],
                        f"{info.get('cpu_percent') or 0.0:.1f}",
                        f"{info.get('memory_percent') or 0.0:.2f}",
                        info.get("status", ""),
                    ])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: float(x[2]), reverse=True)
            _table(
                ["PID", "Name", "CPU%", "MEM%", "Status"],
                procs[:20],
                [7, 30, 7, 7, 10],
            )
        except ImportError:
            self._warn("psutil not installed.")

    # ------------------------------------------------------------------
    # note / notes
    # ------------------------------------------------------------------

    def do_note(self, arg: str) -> None:
        """Save a note.\n  Usage: note <title> <content>"""
        self._record(f"note {arg}")
        parts = arg.split(None, 1)
        if len(parts) < 2:
            self._error("Usage: note <title> <content>")
            return
        title, content = parts[0], parts[1]
        result = self._forward(f"save note '{title}': {content}")
        if result:
            print(textwrap.indent(result, "  "))
        else:
            try:
                from database.db_manager import DatabaseManager  # type: ignore[import]
                db = DatabaseManager()
                db.add_note(title=title, content=content)
                self._info(f"Note '{title}' saved.")
            except Exception as exc:  # noqa: BLE001
                self._error(f"Could not save note: {exc}")

    def do_notes(self, _arg: str) -> None:
        """List all saved notes."""
        self._record("notes")
        self._header("NOTES")
        result = self._forward("list notes")
        if result:
            print(textwrap.indent(result, "  "))
            return
        try:
            from database.db_manager import DatabaseManager  # type: ignore[import]
            db = DatabaseManager()
            notes = db.get_notes()
            if not notes:
                self._info("No notes saved yet.")
                return
            rows = [
                [
                    str(n.get("note_id", "")),
                    n.get("title", ""),
                    (n.get("content") or "")[:40],
                    str(n.get("created_at", ""))[:16],
                ]
                for n in notes
            ]
            _table(["ID", "Title", "Content (preview)", "Created"], rows, [5, 24, 42, 17])
        except Exception as exc:  # noqa: BLE001
            self._error(f"Could not retrieve notes: {exc}")

    # ------------------------------------------------------------------
    # reminder / reminders
    # ------------------------------------------------------------------

    def do_reminder(self, arg: str) -> None:
        """Set a reminder.\n  Usage: reminder <title> <time> <message>"""
        self._record(f"reminder {arg}")
        parts = shlex.split(arg) if arg else []
        if len(parts) < 3:
            self._error("Usage: reminder <title> <time> <message>")
            return
        title, remind_time, message = parts[0], parts[1], " ".join(parts[2:])
        result = self._forward(f"remind me about {title} at {remind_time}: {message}")
        if result:
            print(textwrap.indent(result, "  "))
        else:
            try:
                from database.db_manager import DatabaseManager  # type: ignore[import]
                from datetime import datetime as _dt
                from dateutil import parser as _dp  # type: ignore[import]
                db = DatabaseManager()
                try:
                    remind_dt = _dp.parse(remind_time)
                except Exception:  # noqa: BLE001
                    remind_dt = _dt.now()
                db.add_reminder(title=title, message=message, remind_at=remind_dt)
                self._info(f"Reminder '{title}' set for {remind_time}.")
            except Exception as exc:  # noqa: BLE001
                self._error(f"Could not set reminder: {exc}")

    def do_reminders(self, _arg: str) -> None:
        """List all reminders."""
        self._record("reminders")
        self._header("REMINDERS")
        result = self._forward("list reminders")
        if result:
            print(textwrap.indent(result, "  "))
            return
        try:
            from database.db_manager import DatabaseManager  # type: ignore[import]
            db = DatabaseManager()
            reminders = db.get_all_reminders(include_completed=True)
            if not reminders:
                self._info("No reminders set.")
                return
            rows = [
                [
                    str(r.get("reminder_id", "")),
                    r.get("title", ""),
                    str(r.get("remind_at", ""))[:16],
                    (r.get("message") or "")[:30],
                ]
                for r in reminders
            ]
            _table(["ID", "Title", "Time", "Message"], rows, [5, 22, 18, 32])
        except Exception as exc:  # noqa: BLE001
            self._error(f"Could not retrieve reminders: {exc}")

    # ------------------------------------------------------------------
    # weather
    # ------------------------------------------------------------------

    def do_weather(self, arg: str) -> None:
        """Get weather for a city.\n  Usage: weather <city>"""
        self._record(f"weather {arg}")
        city = arg.strip()
        if not city:
            self._error("Usage: weather <city>")
            return
        self._header(f"WEATHER: {city}")
        result = self._forward(f"weather in {city}")
        if result:
            print(textwrap.indent(result, "  "))
        else:
            self._warn("Weather data unavailable (AI engine not connected).")

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def do_search(self, arg: str) -> None:
        """Perform a web search.\n  Usage: search <query>"""
        self._record(f"search {arg}")
        query = arg.strip()
        if not query:
            self._error("Usage: search <query>")
            return
        self._header(f"SEARCH: {query}")
        result = self._forward(f"search for {query}")
        if result:
            print(textwrap.indent(result, "  "))
        else:
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
            self._info(f"Google URL: {_c(url, _C.CYAN)}")

    # ------------------------------------------------------------------
    # chat
    # ------------------------------------------------------------------

    def do_chat(self, arg: str) -> None:
        """Chat with the Jarvis AI.\n  Usage: chat <message>"""
        self._record(f"chat {arg}")
        message = arg.strip()
        if not message:
            self._error("Usage: chat <message>")
            return
        result = self._forward(message)
        if result:
            print(_c("  Jarvis: ", _C.MAGENTA) + result)
        else:
            self._warn("AI engine not connected. Start Jarvis with --mode=cli.")

    # ------------------------------------------------------------------
    # history
    # ------------------------------------------------------------------

    def do_history(self, _arg: str) -> None:
        """Show command history for this session."""
        self._record("history")
        self._header("COMMAND HISTORY")
        if not self._history:
            self._info("No commands in history yet.")
            return
        for i, cmd_str in enumerate(self._history[-50:], 1):
            print(f"  {_c(str(i).rjust(3), _C.GREY)}  {cmd_str}")

    # ------------------------------------------------------------------
    # help override (augment default)
    # ------------------------------------------------------------------

    def do_help(self, arg: str) -> None:
        """Show help for commands."""
        self._record(f"help {arg}")
        if arg:
            super().do_help(arg)
            return
        self._header("AVAILABLE COMMANDS")
        commands = [
            ("status",             "Show CPU, memory, disk, and uptime"),
            ("execute <cmd>",      "Run a shell command"),
            ("files [path]",       "List files in a directory"),
            ("processes",          "List top running processes"),
            ("note <title> <msg>", "Save a note"),
            ("notes",              "List all notes"),
            ("reminder <t> <t> <m>","Set a reminder"),
            ("reminders",          "List all reminders"),
            ("weather <city>",     "Get weather for a city"),
            ("search <query>",     "Web search"),
            ("chat <message>",     "Chat with Jarvis AI"),
            ("history",            "Show session command history"),
            ("help",               "Show this help"),
            ("exit / quit",        "Exit Jarvis CLI"),
        ]
        for cmd_str, desc in commands:
            print(
                f"  {_c(cmd_str.ljust(26), _C.CYAN)}  "
                f"{_c(desc, _C.WHITE)}"
            )

    # ------------------------------------------------------------------
    # exit / quit
    # ------------------------------------------------------------------

    def do_exit(self, _arg: str) -> bool:
        """Exit the Jarvis CLI."""
        print(_c("\n  Goodbye. JARVIS signing off.\n", _C.CYAN))
        return True

    def do_quit(self, arg: str) -> bool:
        """Exit the Jarvis CLI."""
        return self.do_exit(arg)

    # Ctrl-D
    def do_EOF(self, _arg: str) -> bool:  # noqa: N802
        print()
        return self.do_exit("")

    # ------------------------------------------------------------------
    # Tab completion helpers
    # ------------------------------------------------------------------

    def get_names(self) -> list[str]:
        return [name for name in dir(self.__class__) if name.startswith("do_")]

    def complete_files(self, text: str, _line: str, _begidx: int, _endidx: int) -> list[str]:
        """Tab-complete file paths."""
        import glob as _glob
        return _glob.glob(text + "*")

    def complete_execute(self, text: str, _line: str, _begidx: int, _endidx: int) -> list[str]:
        import glob as _glob
        return _glob.glob(text + "*")


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def run_cli(jarvis_instance: Optional[Any] = None) -> None:
    """Start the interactive Jarvis CLI.

    Args:
        jarvis_instance: Optional :class:`JarvisAI` instance to forward
            commands to.
    """
    try:
        JarvisCLI(jarvis_instance=jarvis_instance).cmdloop()
    except KeyboardInterrupt:
        print(_c("\n\n  Interrupted. JARVIS signing off.\n", _C.CYAN))


if __name__ == "__main__":
    run_cli()
