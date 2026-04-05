"""
Jarvis AI - Advanced Edition
Entry point for the complete AI assistant system.
"""

import sys
import os
import logging
import argparse
import threading

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ai_engine import AIEngine
from core.system_control import SystemControl
from core.voice_engine import VoiceEngine
from core.task_scheduler import TaskScheduler
from core.behavior_analyzer import BehaviorAnalyzer
from intelligence.memory_system import MemorySystem
from intelligence.context_manager import ContextManager
from database.db_manager import DatabaseManager
from api.rest_api import create_api_app
from ui.web_dashboard import create_dashboard_app
from cli.interface import CLIInterface
from utils.config import Config
from utils.logger import setup_logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="Jarvis AI - Advanced AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  cli     - Interactive command-line interface (default)
  web     - Web dashboard only
  api     - REST API server only
  voice   - Voice-only mode
  daemon  - Background daemon (all services)

Examples:
  python jarvis.py
  python jarvis.py --mode web --port 5000
  python jarvis.py --mode daemon
  python jarvis.py --mode cli --debug
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["cli", "web", "api", "voice", "daemon"],
        default="cli",
        help="Run mode (default: cli)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host for web/api server")
    parser.add_argument("--port", type=int, default=None, help="Port override")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--version", action="version", version="Jarvis AI 2.0.0")
    return parser.parse_args()


def initialize_core(config: Config) -> dict:
    """Initialize all core components and return them."""
    logger = logging.getLogger("jarvis")
    logger.info("Initializing Jarvis AI core components...")

    db = DatabaseManager(config)
    db.initialize()

    memory = MemorySystem(config, db)
    context = ContextManager(config, memory)
    ai = AIEngine(config, memory, context)
    system = SystemControl(config)
    scheduler = TaskScheduler(config, db)
    behavior = BehaviorAnalyzer(config, db)

    return {
        "db": db,
        "memory": memory,
        "context": context,
        "ai": ai,
        "system": system,
        "scheduler": scheduler,
        "behavior": behavior,
    }


def run_cli(config: Config, components: dict):
    """Run interactive CLI."""
    cli = CLIInterface(config, components)
    cli.run()


def run_web(config: Config, components: dict, host: str, port: int):
    """Run web dashboard."""
    app = create_dashboard_app(config, components)
    port = port or config.get("web.port", 5000)
    logger = logging.getLogger("jarvis")
    logger.info(f"Starting web dashboard on http://{host}:{port}")
    app.run(host=host, port=port, debug=config.debug)


def run_api(config: Config, components: dict, host: str, port: int):
    """Run REST API server."""
    import uvicorn
    app = create_api_app(config, components)
    port = port or config.get("api.port", 8000)
    logger = logging.getLogger("jarvis")
    logger.info(f"Starting REST API on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def run_voice(config: Config, components: dict):
    """Run voice-only mode."""
    voice = VoiceEngine(config, components["ai"])
    voice.start_listening()


def run_daemon(config: Config, components: dict, host: str):
    """Run all services as a background daemon."""
    logger = logging.getLogger("jarvis")
    logger.info("Starting Jarvis AI in daemon mode...")

    threads = []

    # Start scheduler
    components["scheduler"].start()

    # Start web dashboard in a thread
    web_app = create_dashboard_app(config, components)
    web_port = config.get("web.port", 5000)

    def _web():
        web_app.run(host=host, port=web_port, debug=False, use_reloader=False)

    t_web = threading.Thread(target=_web, daemon=True, name="web-dashboard")
    t_web.start()
    threads.append(t_web)
    logger.info(f"Web dashboard started on http://{host}:{web_port}")

    # Start voice if enabled
    if config.get("voice.enabled", False):
        voice = VoiceEngine(config, components["ai"])

        def _voice():
            voice.start_listening()

        t_voice = threading.Thread(target=_voice, daemon=True, name="voice-engine")
        t_voice.start()
        threads.append(t_voice)
        logger.info("Voice engine started")

    logger.info("Jarvis AI daemon is running. Press Ctrl+C to stop.")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("Shutting down Jarvis AI daemon...")


def main():
    args = parse_args()

    # Load configuration
    config = Config(args.config)
    if args.debug:
        config.debug = True

    # Setup logging
    setup_logger(config)
    logger = logging.getLogger("jarvis")
    logger.info("=" * 60)
    logger.info("  Jarvis AI - Advanced Edition v2.0.0")
    logger.info("=" * 60)

    # Initialize core components
    components = initialize_core(config)

    host = args.host

    try:
        if args.mode == "cli":
            run_cli(config, components)
        elif args.mode == "web":
            run_web(config, components, host, args.port)
        elif args.mode == "api":
            run_api(config, components, host, args.port)
        elif args.mode == "voice":
            run_voice(config, components)
        elif args.mode == "daemon":
            run_daemon(config, components, host)
    except KeyboardInterrupt:
        logger.info("\nJarvis AI stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
