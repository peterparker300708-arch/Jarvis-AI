#!/usr/bin/env python3
"""
Jarvis AI – Complete System Control Assistant
Main entry point
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path when run as a script
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ---------------------------------------------------------------------------
# ANSI colours (best-effort; graceful fallback when not a TTY)
# ---------------------------------------------------------------------------

class _C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    BLUE    = "\033[34m"
    GREY    = "\033[90m"
    MAGENTA = "\033[95m"


def _c(text: str, *codes: str) -> str:
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + text + _C.RESET


# ---------------------------------------------------------------------------
# Startup banner
# ---------------------------------------------------------------------------

_LOGO = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""


def _print_banner(version: str, components: dict[str, bool]) -> None:
    """Print the startup banner with component status."""
    print(_c(_LOGO, _C.CYAN, _C.BOLD))
    print(_c(f"  AI Control System  v{version}", _C.BLUE))
    print(_c("  " + "─" * 54, _C.GREY))
    print()
    for name, ok in components.items():
        icon  = _c("✓", _C.GREEN) if ok else _c("✗", _C.RED)
        label = _c(name.ljust(20), _C.CYAN)
        status = _c("READY", _C.GREEN) if ok else _c("UNAVAILABLE", _C.YELLOW)
        print(f"    {icon}  {label}  {status}")
    print()
    print(_c("  " + "─" * 54, _C.GREY))
    print()


# ---------------------------------------------------------------------------
# Component availability probe
# ---------------------------------------------------------------------------

def _probe_components(config: dict[str, Any], voice_enabled: bool) -> dict[str, bool]:
    """Attempt to import optional dependencies and return availability map."""
    components: dict[str, bool] = {}

    # psutil (system monitoring)
    try:
        import psutil  # noqa: F401
        components["System Monitor"] = True
    except ImportError:
        components["System Monitor"] = False

    # Database
    try:
        from database.db_manager import DatabaseManager  # noqa: F401
        components["Database"] = True
    except Exception:  # noqa: BLE001
        components["Database"] = False

    # AI engine
    try:
        from core.ai_engine import AIEngine  # noqa: F401
        components["AI Engine"] = True
    except Exception:  # noqa: BLE001
        components["AI Engine"] = False

    # Voice
    if voice_enabled:
        try:
            import pyttsx3  # noqa: F401
            import speech_recognition  # noqa: F401
            components["Voice Engine"] = True
        except ImportError:
            components["Voice Engine"] = False
    else:
        components["Voice Engine (disabled)"] = False

    # Web / Flask
    try:
        import flask  # noqa: F401
        components["Web Dashboard"] = True
    except ImportError:
        components["Web Dashboard"] = False

    # Scheduler
    try:
        from core.task_scheduler import TaskScheduler  # noqa: F401
        components["Task Scheduler"] = True
    except Exception:  # noqa: BLE001
        components["Task Scheduler"] = False

    return components


# ---------------------------------------------------------------------------
# JarvisAI  – main orchestrator
# ---------------------------------------------------------------------------

class JarvisAI:
    """Central Jarvis AI orchestrator.

    Initialises all sub-systems and dispatches commands to the appropriate
    handler depending on the active mode.

    Args:
        config:        Application configuration dictionary (from config.yaml).
        voice_enabled: Whether the voice engine should be started.
        debug:         Enable debug logging throughout.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        config: dict[str, Any],
        voice_enabled: bool = True,
        debug: bool = False,
    ) -> None:
        self._config        = config
        self._voice_enabled = voice_enabled
        self._debug         = debug
        self._running       = False

        # Sub-system references (populated in _init_components)
        self._db:        Optional[Any] = None
        self._ai:        Optional[Any] = None
        self._voice:     Optional[Any] = None
        self._scheduler: Optional[Any] = None

        self._components = self._init_components()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_components(self) -> dict[str, bool]:
        """Initialise sub-systems and return an availability map."""
        status: dict[str, bool] = {}

        # Database
        try:
            from database.db_manager import DatabaseManager
            db_path = self._config.get("database", {}).get("path", "jarvis.db")
            self._db = DatabaseManager(db_path=db_path)
            status["Database"] = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"Database init failed: {exc}")
            status["Database"] = False

        # AI engine
        try:
            from core.ai_engine import AIEngine
            ai_cfg = self._config.get("ai", {})
            self._ai = AIEngine(
                model=ai_cfg.get("model", "mistral"),
                base_url=ai_cfg.get("base_url", "http://localhost:11434"),
                temperature=float(ai_cfg.get("temperature", 0.7)),
                max_tokens=int(ai_cfg.get("max_tokens", 2000)),
            )
            status["AI Engine"] = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"AI engine init failed: {exc}")
            status["AI Engine"] = False

        # Voice engine
        if self._voice_enabled:
            try:
                from core.voice_engine import VoiceEngine
                v_cfg = self._config.get("voice", {})
                self._voice = VoiceEngine(
                    speech_rate=int(v_cfg.get("speech_rate", 175)),
                    volume=float(v_cfg.get("volume", 0.9)),
                    language=v_cfg.get("language", "en-US"),
                )
                status["Voice Engine"] = True
            except Exception as exc:  # noqa: BLE001
                _log_warn(f"Voice engine init failed: {exc}")
                status["Voice Engine"] = False
        else:
            status["Voice Engine (disabled)"] = False

        # Task scheduler
        try:
            from core.task_scheduler import TaskScheduler
            self._scheduler = TaskScheduler()
            status["Task Scheduler"] = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"Task scheduler init failed: {exc}")
            status["Task Scheduler"] = False

        # System monitor probe
        try:
            import psutil  # noqa: F401
            status["System Monitor"] = True
        except ImportError:
            status["System Monitor"] = False

        # Flask
        try:
            import flask  # noqa: F401
            status["Web Dashboard"] = True
        except ImportError:
            status["Web Dashboard"] = False

        return status

    # ------------------------------------------------------------------
    # Command processor
    # ------------------------------------------------------------------

    def process_command(self, text: str) -> str:
        """Unified command processor.

        Routes the command through the AI engine if available, falls back to
        built-in rule-based handling.

        Args:
            text: Raw user command / utterance.

        Returns:
            String response to display or speak.
        """
        text = text.strip()
        if not text:
            return ""

        # Log command to DB
        if self._db is not None:
            try:
                self._db.log_command(command=text)
            except Exception:  # noqa: BLE001
                pass

        # Route through AI engine
        if self._ai is not None:
            try:
                response = self._ai.process(text)
                if response:
                    return response
            except Exception as exc:  # noqa: BLE001
                _log_warn(f"AI engine error: {exc}")

        # Minimal built-in fallback
        return self._builtin_handler(text)

    def _builtin_handler(self, text: str) -> str:
        """Simple rule-based fallback when AI is unavailable."""
        lower = text.lower()

        if any(w in lower for w in ("hello", "hi ", "hey")):
            return "Hello! I'm Jarvis. How can I assist you?"

        if "time" in lower:
            from datetime import datetime
            return f"The current time is {datetime.now().strftime('%H:%M:%S')}."

        if "date" in lower:
            from datetime import datetime
            return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."

        if any(w in lower for w in ("status", "system", "cpu", "memory")):
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory().percent
                return (
                    f"System status: CPU {cpu:.1f}%, "
                    f"Memory {mem:.1f}% used."
                )
            except ImportError:
                return "psutil not installed – cannot retrieve system stats."

        if "help" in lower:
            return (
                "I can help with: time, date, system status, notes, reminders, "
                "weather, web search, and general conversation."
            )

        return f"I received your command: '{text}'. AI engine is currently unavailable."

    # ------------------------------------------------------------------
    # Start modes
    # ------------------------------------------------------------------

    def start(self, mode: str = "cli") -> None:
        """Start Jarvis in the specified mode.

        Args:
            mode: One of ``cli``, ``web``, ``api``, ``voice``, ``daemon``.
        """
        self._running = True
        _print_banner(self.VERSION, self._components)

        if mode == "cli":
            self._start_cli()
        elif mode == "web":
            self._start_web()
        elif mode == "api":
            self._start_api()
        elif mode == "voice":
            self._start_voice()
        elif mode == "daemon":
            self._start_daemon()
        else:
            print(_c(f"  Unknown mode '{mode}'. Defaulting to CLI.", _C.YELLOW))
            self._start_cli()

    # -- CLI --

    def _start_cli(self) -> None:
        from cli.interface import run_cli
        run_cli(jarvis_instance=self)

    # -- Web dashboard --

    def _start_web(self) -> None:
        web_cfg = self._config.get("web", {})
        host    = web_cfg.get("host", "0.0.0.0")
        port    = int(web_cfg.get("port", 8080))
        debug   = bool(web_cfg.get("debug", False)) or self._debug
        secret  = web_cfg.get("secret_key", "jarvis-dashboard-secret")

        print(_c(f"  Starting Web Dashboard → http://{host}:{port}/", _C.CYAN))
        from web.app import start_dashboard
        start_dashboard(
            host=host,
            port=port,
            debug=debug,
            jarvis_instance=self,
            secret_key=secret,
        )

    # -- REST API --

    def _start_api(self) -> None:
        api_cfg = self._config.get("api", {})
        host    = api_cfg.get("host", "0.0.0.0")
        port    = int(api_cfg.get("port", 5000))
        debug   = bool(api_cfg.get("debug", False)) or self._debug
        api_key = api_cfg.get("api_key") or os.environ.get("JARVIS_API_KEY", "")

        print(_c(f"  Starting REST API → http://{host}:{port}/", _C.CYAN))
        from api.rest_api import create_app
        from api.routes import register_routes
        app = create_app(api_key=api_key or None, debug=debug)
        register_routes(app)
        app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)

    # -- Voice mode --

    def _start_voice(self) -> None:
        if self._voice is None:
            print(_c("  Voice engine unavailable. Falling back to CLI.", _C.YELLOW))
            self._start_cli()
            return

        wake = self._config.get("jarvis", {}).get("wake_word", "jarvis")
        print(_c(f"  Voice mode active. Wake word: '{wake}'", _C.CYAN))
        print(_c("  Listening… (Ctrl-C to stop)", _C.GREY))

        try:
            while self._running:
                text = self._voice.listen()
                if text and wake.lower() in text.lower():
                    command = text.lower().replace(wake.lower(), "").strip()
                    if command:
                        response = self.process_command(command)
                        print(_c(f"  Jarvis: {response}", _C.MAGENTA))
                        self._voice.speak(response)
        except KeyboardInterrupt:
            print(_c("\n  Voice mode stopped.", _C.YELLOW))

    # -- Daemon mode --

    def _start_daemon(self) -> None:
        """Run both the web dashboard and REST API concurrently."""
        import threading

        print(_c("  Starting in daemon mode (web + api)…", _C.CYAN))

        web_thread = threading.Thread(target=self._start_web, daemon=True, name="web")
        api_thread = threading.Thread(target=self._start_api, daemon=True, name="api")

        web_thread.start()
        time.sleep(0.5)
        api_thread.start()

        print(_c("  Daemon running. Press Ctrl-C to stop.", _C.GREY))
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Gracefully stop all running sub-systems."""
        self._running = False
        print(_c("\n  Shutting down Jarvis…", _C.YELLOW))

        if self._scheduler is not None:
            try:
                self._scheduler.shutdown()
            except Exception:  # noqa: BLE001
                pass

        if self._voice is not None:
            try:
                self._voice.stop()
            except Exception:  # noqa: BLE001
                pass

        print(_c("  JARVIS offline. Goodbye.\n", _C.CYAN))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_warn(msg: str) -> None:
    print(_c(f"  [WARN] {msg}", _C.YELLOW), file=sys.stderr)


def _load_config(path: str = "config.yaml") -> dict[str, Any]:
    """Load YAML configuration, falling back to an empty dict on failure."""
    try:
        import yaml  # type: ignore[import]
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        _log_warn(f"Config file '{path}' not found. Using defaults.")
        return {}
    except Exception as exc:  # noqa: BLE001
        _log_warn(f"Failed to load config: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="Jarvis AI – Complete System Control Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap_dedent(
            """
            Examples:
              jarvis                        # start in CLI mode (default)
              jarvis --mode web             # start web dashboard on :8080
              jarvis --mode api             # start REST API on :5000
              jarvis --mode voice           # start voice assistant
              jarvis --mode daemon          # start web + api concurrently
              jarvis --mode web --port 9090 # web dashboard on custom port
              jarvis --debug                # enable debug logging
            """
        ),
    )

    parser.add_argument(
        "--mode",
        choices=["cli", "web", "api", "voice", "daemon"],
        default="cli",
        help="Operating mode (default: cli)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Network host to bind API/web server (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="TCP port for API (default: 5000) or web (default: 8080)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug / verbose mode",
    )
    parser.add_argument(
        "--no-voice",
        dest="no_voice",
        action="store_true",
        default=False,
        help="Disable voice engine even in voice/daemon mode",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        metavar="PATH",
        help="Path to YAML config file (default: config.yaml)",
    )

    return parser


def textwrap_dedent(text: str) -> str:
    import textwrap
    return textwrap.dedent(text)


# ---------------------------------------------------------------------------
# Signal handlers
# ---------------------------------------------------------------------------

_jarvis_instance: Optional[JarvisAI] = None


def _handle_signal(signum: int, _frame: Any) -> None:
    sig_name = signal.Signals(signum).name
    print(_c(f"\n  Received {sig_name}.", _C.YELLOW))
    if _jarvis_instance is not None:
        _jarvis_instance.shutdown()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse arguments, load config, create JarvisAI, and start."""
    global _jarvis_instance  # noqa: PLW0603

    parser = _build_parser()
    args   = parser.parse_args()

    # Load configuration
    config = _load_config(args.config)

    # Apply CLI overrides to config
    if args.host:
        config.setdefault("web", {})["host"] = args.host
        config.setdefault("api", {})["host"] = args.host
    if args.port:
        if args.mode == "web":
            config.setdefault("web", {})["port"] = args.port
        else:
            config.setdefault("api", {})["port"] = args.port
    if args.debug:
        config.setdefault("web", {})["debug"] = True
        config.setdefault("api", {})["debug"] = True

    # Determine voice enable state
    voice_cfg     = config.get("voice", {})
    voice_enabled = voice_cfg.get("enabled", True) and not args.no_voice

    # Install signal handlers
    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Create and start Jarvis
    jarvis = JarvisAI(
        config=config,
        voice_enabled=voice_enabled,
        debug=args.debug,
    )
    _jarvis_instance = jarvis

    try:
        jarvis.start(mode=args.mode)
    except KeyboardInterrupt:
        jarvis.shutdown()
    except Exception as exc:
        print(_c(f"\n  Fatal error: {exc}", _C.RED), file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
