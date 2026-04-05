"""External integrations: GitHub, Weather (wttr.in), News (RSS), Telegram bot."""

from __future__ import annotations

import html
import re
import urllib.parse
from typing import Any, Dict, List, Optional

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": "JarvisAI/1.0 (https://github.com/JarvisAI)",
    "Accept": "application/json",
}
_TIMEOUT = 15


# ======================================================================
# GitHub Integration
# ======================================================================

class GitHubIntegration:
    """Interact with the GitHub REST API v3.

    Supports both authenticated (with token) and anonymous access.
    Anonymous access is subject to stricter rate limits (60 req/hr).

    Args:
        token: Optional GitHub personal access token.
        username: GitHub username (used for repo listing when token absent).
    """

    _BASE = "https://api.github.com"

    def __init__(self, token: str = "", username: str = "") -> None:
        self.token = token
        self.username = username
        self._headers = dict(_DEFAULT_HEADERS)
        if token:
            self._headers["Authorization"] = f"token {token}"

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        if not _REQUESTS_AVAILABLE:
            return {"error": "requests not installed"}
        url = f"{self._BASE}{path}"
        try:
            resp = _requests.get(url, headers=self._headers, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.error("GitHub GET %s error: %s", path, exc)
            return {"error": str(exc)}

    def _post(self, path: str, json_body: Dict) -> Any:
        if not _REQUESTS_AVAILABLE:
            return {"error": "requests not installed"}
        url = f"{self._BASE}{path}"
        try:
            resp = _requests.post(url, headers=self._headers, json=json_body, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.error("GitHub POST %s error: %s", path, exc)
            return {"error": str(exc)}

    def get_repos(self, user: Optional[str] = None, per_page: int = 30) -> List[Dict[str, Any]]:
        """List public repositories for *user* (or the authenticated user).

        Returns:
            List of dicts: {name, full_name, description, url, stars, language, private}.
        """
        target = user or self.username
        if not target and self.token:
            data = self._get("/user/repos", {"per_page": per_page, "sort": "updated"})
        elif target:
            data = self._get(f"/users/{target}/repos", {"per_page": per_page, "sort": "updated"})
        else:
            return [{"error": "No username or token provided"}]

        if isinstance(data, dict) and "error" in data:
            return [data]

        return [
            {
                "name": r.get("name"),
                "full_name": r.get("full_name"),
                "description": r.get("description", ""),
                "url": r.get("html_url"),
                "stars": r.get("stargazers_count", 0),
                "language": r.get("language", ""),
                "private": r.get("private", False),
                "updated_at": r.get("updated_at", ""),
            }
            for r in data
            if isinstance(r, dict)
        ]

    def create_issue(self, repo: str, title: str, body: str = "", labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a GitHub issue.

        Args:
            repo: Repository in ``owner/name`` format.
            title: Issue title.
            body: Issue body (Markdown).
            labels: Optional list of label names.

        Returns:
            dict with issue details or error.
        """
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        data = self._post(f"/repos/{repo}/issues", payload)
        if isinstance(data, dict) and "error" not in data:
            return {
                "issue_number": data.get("number"),
                "title": data.get("title"),
                "url": data.get("html_url"),
                "state": data.get("state"),
            }
        return data

    def list_issues(self, repo: str, state: str = "open", per_page: int = 20) -> List[Dict[str, Any]]:
        """List issues for a repository.

        Args:
            repo: Repository in ``owner/name`` format.
            state: "open", "closed", or "all".

        Returns:
            List of issue dicts.
        """
        data = self._get(f"/repos/{repo}/issues", {"state": state, "per_page": per_page})
        if isinstance(data, dict) and "error" in data:
            return [data]
        return [
            {
                "number": i.get("number"),
                "title": i.get("title"),
                "state": i.get("state"),
                "url": i.get("html_url"),
                "author": i.get("user", {}).get("login", ""),
                "created_at": i.get("created_at", ""),
            }
            for i in data
            if isinstance(i, dict)
        ]


# ======================================================================
# Weather Integration (wttr.in)
# ======================================================================

class WeatherIntegration:
    """Free weather data from wttr.in — no API key required."""

    _BASE = "https://wttr.in"

    def get_weather(self, city: str) -> Dict[str, Any]:
        """Get current weather conditions for *city*.

        Returns:
            dict with condition, temperature, humidity, wind speed, etc.
        """
        if not _REQUESTS_AVAILABLE:
            return {"error": "requests not installed"}

        encoded = urllib.parse.quote_plus(city)
        url = f"{self._BASE}/{encoded}?format=j1"
        try:
            resp = _requests.get(url, headers=_DEFAULT_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error("Weather fetch error: %s", exc)
            return {"error": str(exc), "city": city}

        try:
            cur = data["current_condition"][0]
            area = data.get("nearest_area", [{}])[0]
            area_name = area.get("areaName", [{}])[0].get("value", city)
            return {
                "city": area_name,
                "condition": cur.get("weatherDesc", [{}])[0].get("value", ""),
                "temperature_c": cur.get("temp_C"),
                "temperature_f": cur.get("temp_F"),
                "feels_like_c": cur.get("FeelsLikeC"),
                "humidity": cur.get("humidity"),
                "wind_kmh": cur.get("windspeedKmph"),
                "wind_direction": cur.get("winddir16Point"),
                "visibility_km": cur.get("visibility"),
                "uv_index": cur.get("uvIndex"),
                "cloud_cover": cur.get("cloudcover"),
                "pressure_mb": cur.get("pressure"),
            }
        except (KeyError, IndexError, TypeError) as exc:
            return {"error": f"Parse error: {exc}", "city": city}

    def get_forecast(self, city: str, days: int = 3) -> List[Dict[str, Any]]:
        """Get a multi-day weather forecast for *city*.

        Args:
            city: City name.
            days: Number of forecast days (max 3 from wttr.in free tier).

        Returns:
            List of daily forecast dicts.
        """
        if not _REQUESTS_AVAILABLE:
            return [{"error": "requests not installed"}]

        encoded = urllib.parse.quote_plus(city)
        url = f"{self._BASE}/{encoded}?format=j1"
        try:
            resp = _requests.get(url, headers=_DEFAULT_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error("Forecast fetch error: %s", exc)
            return [{"error": str(exc)}]

        forecast = []
        for day_data in data.get("weather", [])[:days]:
            hourly = day_data.get("hourly", [])
            avg_temp_c = None
            if hourly:
                temps = [int(h.get("tempC", 0)) for h in hourly]
                avg_temp_c = round(sum(temps) / len(temps), 1) if temps else None

            forecast.append(
                {
                    "date": day_data.get("date"),
                    "max_temp_c": day_data.get("maxtempC"),
                    "min_temp_c": day_data.get("mintempC"),
                    "avg_temp_c": avg_temp_c,
                    "condition": day_data.get("hourly", [{}])[len(hourly) // 2].get(
                        "weatherDesc", [{}]
                    )[0].get("value", ""),
                    "sunrise": day_data.get("astronomy", [{}])[0].get("sunrise", ""),
                    "sunset": day_data.get("astronomy", [{}])[0].get("sunset", ""),
                    "uv_index": day_data.get("uvIndex"),
                }
            )
        return forecast


# ======================================================================
# News Integration (public RSS feeds)
# ======================================================================

_RSS_FEEDS: Dict[str, str] = {
    "general": "https://feeds.bbci.co.uk/news/rss.xml",
    "technology": "https://feeds.feedburner.com/TechCrunch",
    "science": "https://www.sciencedaily.com/rss/top/science.xml",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "sports": "https://feeds.bbci.co.uk/sport/rss.xml",
    "health": "https://feeds.bbci.co.uk/news/health/rss.xml",
    "entertainment": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    "us": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
}


class NewsIntegration:
    """Fetch news headlines from free RSS feeds — no API key required."""

    def get_headlines(self, category: str = "general", count: int = 10) -> List[Dict[str, str]]:
        """Fetch headlines for the given *category*.

        Args:
            category: One of general, technology, science, business,
                      world, sports, health, entertainment, us.
            count: Maximum number of items to return.

        Returns:
            List of dicts: {title, url, summary, published, source}.
        """
        if not _REQUESTS_AVAILABLE:
            return [{"error": "requests not installed"}]

        feed_url = _RSS_FEEDS.get(category.lower(), _RSS_FEEDS["general"])
        try:
            resp = _requests.get(feed_url, headers=_DEFAULT_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("News fetch error: %s", exc)
            return [{"error": str(exc)}]

        try:
            from bs4 import BeautifulSoup  # noqa: PLC0415
            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all("item")[:count]
            results: List[Dict[str, str]] = []
            for item in items:
                title_tag = item.find("title")
                link_tag = item.find("link")
                desc_tag = item.find("description")
                pub_tag = item.find("pubDate")
                source_tag = item.find("source")
                results.append(
                    {
                        "title": html.unescape(title_tag.text.strip()) if title_tag else "",
                        "url": link_tag.text.strip() if link_tag else "",
                        "summary": html.unescape(
                            re.sub(r"<[^>]+>", "", desc_tag.text).strip()[:400]
                        ) if desc_tag else "",
                        "published": pub_tag.text.strip() if pub_tag else "",
                        "source": source_tag.text.strip() if source_tag else category,
                        "category": category,
                    }
                )
            return results
        except ImportError:
            # Fallback: basic regex XML parse
            titles = re.findall(r"<title><!\[CDATA\[(.+?)\]\]></title>|<title>(.+?)</title>", resp.text)
            links = re.findall(r"<link>(.+?)</link>", resp.text)
            items_parsed = []
            for i, (t1, t2) in enumerate(titles[:count]):
                title = html.unescape(t1 or t2)
                url = links[i] if i < len(links) else ""
                items_parsed.append({"title": title, "url": url, "summary": "", "published": "", "source": category, "category": category})
            return items_parsed
        except Exception as exc:
            logger.error("RSS parse error: %s", exc)
            return [{"error": f"Parse error: {exc}"}]


# ======================================================================
# Telegram Bot Integration
# ======================================================================

class TelegramBot:
    """Telegram bot integration for Jarvis.

    Requires the ``python-telegram-bot`` package (v20+).

    Args:
        token: Telegram bot token from BotFather.
        jarvis_instance: Optional Jarvis core object with a ``process(text)`` method.
    """

    def __init__(self, token: str = "", jarvis_instance: Any = None) -> None:
        self.token = token
        self.jarvis = jarvis_instance
        self._app: Any = None

    def start_bot(self, token: Optional[str] = None, jarvis_instance: Any = None) -> None:
        """Build and start the Telegram bot (blocking).

        Registers /start, /status, /command <text> handlers.

        Args:
            token: Bot token (overrides constructor value).
            jarvis_instance: Optional Jarvis instance.
        """
        _token = token or self.token
        if jarvis_instance:
            self.jarvis = jarvis_instance

        if not _token:
            logger.error("Telegram bot token not provided.")
            return

        try:
            from telegram import Update  # noqa: PLC0415
            from telegram.ext import (  # noqa: PLC0415
                Application,
                CommandHandler,
                ContextTypes,
                MessageHandler,
                filters,
            )
        except ImportError:
            logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
            return

        async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
            await update.message.reply_text(
                "👋 Hello! I am *Jarvis AI*.\n\n"
                "Commands:\n"
                "  /status — system status\n"
                "  /command <text> — run a command\n"
                "  Or just send me a message!",
                parse_mode="Markdown",
            )

        async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
            try:
                from modules.system_monitor import SystemMonitor  # noqa: PLC0415
                monitor = SystemMonitor()
                snap = monitor.get_snapshot()
                msg = (
                    f"*System Status*\n"
                    f"CPU: {snap['cpu_percent']}% ({snap['cpu_count']} cores)\n"
                    f"RAM: {snap['memory_percent']}% used\n"
                    f"Disk: {snap['disk_percent']}% used\n"
                    f"Uptime: {snap['uptime_str']}"
                )
            except Exception as exc:
                msg = f"Could not retrieve system status: {exc}"
            await update.message.reply_text(msg, parse_mode="Markdown")

        async def cmd_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
            text = " ".join(ctx.args or []).strip()
            if not text:
                await update.message.reply_text("Usage: /command <your command>")
                return
            response = self._process_command(text)
            await update.message.reply_text(response)

        async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
            text = (update.message.text or "").strip()
            if text:
                response = self._process_command(text)
                await update.message.reply_text(response)

        app = Application.builder().token(_token).build()
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("status", cmd_status))
        app.add_handler(CommandHandler("command", cmd_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        self._app = app
        logger.info("Starting Telegram bot...")
        app.run_polling()

    def _process_command(self, text: str) -> str:
        """Route a text command through Jarvis or return an echo."""
        if self.jarvis and hasattr(self.jarvis, "process"):
            try:
                return str(self.jarvis.process(text))
            except Exception as exc:
                logger.error("Jarvis process error: %s", exc)
                return f"Error processing command: {exc}"
        return f"Echo: {text}"

    def stop_bot(self) -> None:
        """Stop the running Telegram bot."""
        if self._app:
            try:
                self._app.stop()
            except Exception as exc:
                logger.warning("Error stopping Telegram bot: %s", exc)
