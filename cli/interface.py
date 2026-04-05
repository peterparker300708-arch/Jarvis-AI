"""
CLI Interface - Interactive command-line interface for Jarvis AI.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Dict, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


BANNER = r"""
  _  _   ____    _    __   __ _  ____      _    ___
 | || | / _  |  / \  |  \ / /| |/ ___|    / \  |_ _|
 | || || |_| | / _ \ | |\ V/ | \___ \    / _ \  | |
 |__  _|  _  |/ ___ \| | | |  |  ___) | / ___ \ | |
    |_| |_| |_/_/   \_\_| |_|  |_|____/ /_/   \_\___|

  Advanced AI Assistant v2.0.0  |  Type 'help' for commands
"""


class CLIInterface:
    """Interactive command-line interface with rich formatting."""

    BUILT_IN_COMMANDS = {
        "help": "Show available commands",
        "status": "Show system status",
        "history": "Show command history",
        "notes": "List saved notes",
        "note <content>": "Save a quick note",
        "tasks": "Show pending tasks",
        "schedule <title> <time>": "Schedule a task (time: YYYY-MM-DD HH:MM)",
        "clear": "Clear the terminal",
        "memory": "Show conversation memory",
        "clear-memory": "Clear conversation memory",
        "profile": "Show behavioral profile",
        "jobs": "Show scheduled jobs",
        "exit / quit": "Exit Jarvis AI",
    }

    def __init__(self, config: Config, components: Dict):
        self.config = config
        self.components = components
        self.ai = components.get("ai")
        self.system = components.get("system")
        self.memory = components.get("memory")
        self.db = components.get("db")
        self.scheduler = components.get("scheduler")
        self.behavior = components.get("behavior")
        self._running = False
        self._history: list = []

    # ------------------------------------------------------------------

    def run(self):
        """Start the interactive CLI loop."""
        self._running = True
        try:
            self._use_rich = self._check_rich()
        except Exception:
            self._use_rich = False

        print(BANNER)
        if self.ai and not self.ai.is_available():
            print("⚠️  AI backend (Ollama) is not running. Responses will use fallback mode.\n")

        while self._running:
            try:
                user_input = self._prompt()
                if user_input is None:
                    break
                user_input = user_input.strip()
                if not user_input:
                    continue
                self._handle_input(user_input)
            except KeyboardInterrupt:
                print("\n(Ctrl+C pressed — type 'exit' to quit)")
            except EOFError:
                break

        print("\nGoodbye! Jarvis AI shut down.")

    def _prompt(self) -> Optional[str]:
        """Display the prompt and read input."""
        try:
            return input("\n🤖 You: ")
        except EOFError:
            return None

    def _handle_input(self, text: str):
        """Route input to built-in commands or AI."""
        self._history.append({"input": text, "timestamp": datetime.now().isoformat()})
        lower = text.lower().strip()

        if lower in ("exit", "quit", "bye"):
            self._running = False
            return

        if lower == "help":
            self._show_help()
            return

        if lower == "status":
            self._show_status()
            return

        if lower == "history":
            self._show_history()
            return

        if lower == "notes":
            self._show_notes()
            return

        if lower.startswith("note "):
            self._save_note(text[5:])
            return

        if lower == "tasks":
            self._show_tasks()
            return

        if lower == "memory":
            self._show_memory()
            return

        if lower == "clear-memory":
            if self.memory:
                self.memory.clear_short_term()
            print("✅ Memory cleared.")
            return

        if lower == "profile":
            self._show_profile()
            return

        if lower == "jobs":
            self._show_jobs()
            return

        if lower == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            return

        # Fall through to AI
        self._ai_chat(text)

    # ------------------------------------------------------------------
    # Built-in command handlers
    # ------------------------------------------------------------------

    def _show_help(self):
        print("\n📖 Available Commands:\n")
        max_len = max(len(k) for k in self.BUILT_IN_COMMANDS)
        for cmd, desc in self.BUILT_IN_COMMANDS.items():
            print(f"  {cmd:<{max_len + 4}} {desc}")
        print("\nAny other input will be sent to Jarvis AI for a response.")

    def _show_status(self):
        if not self.system:
            print("System control not available.")
            return
        status = self.system.get_system_status()
        print(f"\n📊 System Status ({status.get('platform', 'unknown')}):")
        print(f"  CPU:   {status.get('cpu_percent', 0)}%")
        print(f"  RAM:   {status.get('ram_percent', 0)}% ({status.get('ram_used_gb', 0):.1f}/{status.get('ram_total_gb', 0):.1f} GB)")
        print(f"  Disk:  {status.get('disk_percent', 0)}% ({status.get('disk_used_gb', 0):.1f}/{status.get('disk_total_gb', 0):.1f} GB)")
        print(f"  AI:    {'Online ✅' if self.ai and self.ai.is_available() else 'Offline ❌'}")

    def _show_history(self):
        if not self.db:
            print("Database not available.")
            return
        rows = self.db.get_command_history(10)
        if not rows:
            print("No history found.")
            return
        print("\n📜 Recent Commands:")
        for row in rows:
            ts = row.get("created_at", "")[:19] if row.get("created_at") else ""
            status = "✅" if row.get("success") else "❌"
            print(f"  {status} [{ts}] {row.get('command', '')[:60]}")

    def _show_notes(self):
        if not self.db:
            print("Database not available.")
            return
        notes = self.db.get_notes(5)
        if not notes:
            print("No notes saved yet. Use 'note <content>' to add one.")
            return
        print("\n📝 Recent Notes:")
        for n in notes:
            print(f"  [{n.get('id')}] {n.get('title') or n.get('content', '')[:60]}")

    def _save_note(self, content: str):
        if not self.db:
            print("Database not available.")
            return
        note_id = self.db.save_note("", content)
        print(f"✅ Note saved (ID: {note_id})")

    def _show_tasks(self):
        if not self.db:
            print("Database not available.")
            return
        tasks = self.db.get_pending_tasks()
        if not tasks:
            print("No pending tasks.")
            return
        print("\n📅 Pending Tasks:")
        for t in tasks:
            print(f"  [{t.get('priority', 'medium').upper()}] {t.get('title', '')} — {t.get('scheduled_time', '')[:16]}")

    def _show_memory(self):
        if not self.memory:
            print("Memory system not available.")
            return
        history = self.memory.get_recent(5)
        if not history:
            print("No conversation history.")
            return
        print("\n🧠 Recent Memory:")
        for entry in reversed(history):
            role = entry.get("role", "unknown")
            content = entry.get("content", "")[:80]
            print(f"  [{role.upper()}] {content}")

    def _show_profile(self):
        if not self.behavior:
            print("Behavior analyzer not available.")
            return
        profile = self.behavior.get_behavioral_profile()
        print("\n🧑 Behavioral Profile:")
        print(f"  Total commands:  {profile.get('total_commands', 0)}")
        print(f"  Success rate:    {profile.get('success_rate', 0) * 100:.0f}%")
        print(f"  Session length:  {profile.get('session_duration_minutes', 0)} minutes")
        top = profile.get("top_categories", [])
        if top:
            print(f"  Top categories:  {', '.join(c['category'] for c in top[:3])}")

    def _show_jobs(self):
        if not self.scheduler:
            print("Scheduler not available.")
            return
        jobs = self.scheduler.get_jobs()
        if not jobs:
            print("No scheduled jobs.")
            return
        print("\n⏰ Scheduled Jobs:")
        for j in jobs:
            print(f"  [{j.get('type', 'unknown')}] {j.get('name', '')} — next: {j.get('next_run', 'N/A')}")

    def _ai_chat(self, text: str):
        """Send input to the AI engine and display the response."""
        if not self.ai:
            print("AI engine not initialized.")
            return

        # Record behavior
        if self.behavior:
            self.behavior.record_command(text, "chat")

        # Memory
        if self.memory:
            self.memory.add("user", text)

        print("\n🤖 Jarvis: ", end="", flush=True)

        # Try streaming
        try:
            response_parts = []
            for token in self.ai.stream_chat(text):
                print(token, end="", flush=True)
                response_parts.append(token)
            response = "".join(response_parts)
            print()  # newline after streaming
        except Exception:
            response = self.ai.chat(text)
            print(response)

        if self.memory:
            self.memory.add("assistant", response)

        if self.db:
            self.db.log_command(text, "chat", response=response[:500])

    # ------------------------------------------------------------------

    @staticmethod
    def _check_rich() -> bool:
        try:
            import rich  # noqa: F401
            return True
        except ImportError:
            return False
