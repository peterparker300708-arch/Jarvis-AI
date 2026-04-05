"""Web browsing module: search, fetch, weather, news, and page summarisation."""

from __future__ import annotations

import html
import re
import textwrap
import urllib.parse
import webbrowser
from typing import Any, Dict, List, Optional

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
_TIMEOUT = 10

_SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "duckduckgo": "https://html.duckduckgo.com/html/?q={query}",
}

_NEWS_RSS: Dict[str, str] = {
    "technology": "https://feeds.feedburner.com/TechCrunch",
    "science": "https://www.sciencedaily.com/rss/top/science.xml",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "general": "https://feeds.bbci.co.uk/news/rss.xml",
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "sports": "https://feeds.bbci.co.uk/sport/rss.xml",
    "health": "https://feeds.bbci.co.uk/news/health/rss.xml",
    "entertainment": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
}


class WebBrowser:
    """Web browsing utilities with no mandatory API keys.

    Uses requests + BeautifulSoup for scraping, wttr.in for weather,
    and public RSS feeds for news.
    """

    def __init__(self, timeout: int = _TIMEOUT) -> None:
        self.timeout = timeout
        self._session: Optional[Any] = None
        if _REQUESTS_AVAILABLE:
            self._session = requests.Session()
            self._session.headers.update(_DEFAULT_HEADERS)

    # ------------------------------------------------------------------
    # Web search
    # ------------------------------------------------------------------

    def search(self, query: str, engine: str = "duckduckgo") -> List[Dict[str, str]]:
        """Search the web and return result snippets.

        Parses HTML search result pages from DuckDuckGo (default) or Google.

        Args:
            query: Search query string.
            engine: One of "google", "bing", "duckduckgo".

        Returns:
            List of dicts: {title, url, snippet}.
        """
        if not _REQUESTS_AVAILABLE or not _BS4_AVAILABLE:
            return [{"title": "Unavailable", "url": "", "snippet": "requests/BeautifulSoup not installed"}]

        engine = engine.lower()
        if engine not in _SEARCH_ENGINES:
            engine = "duckduckgo"

        url = _SEARCH_ENGINES[engine].format(query=urllib.parse.quote_plus(query))
        try:
            resp = self._session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("Search request failed: %s", exc)
            return [{"title": "Error", "url": "", "snippet": str(exc)}]

        soup = BeautifulSoup(resp.text, "html.parser")

        if engine == "duckduckgo":
            return self._parse_ddg(soup)
        if engine == "google":
            return self._parse_google(soup)
        if engine == "bing":
            return self._parse_bing(soup)
        return []

    # ------------------------------------------------------------------
    # Page fetching
    # ------------------------------------------------------------------

    def get_page(self, url: str) -> str:
        """Fetch the plain-text content of a web page.

        Args:
            url: Full URL to fetch.

        Returns:
            Cleaned plain-text content of the page.
        """
        if not _REQUESTS_AVAILABLE:
            return "requests library not available"

        try:
            resp = self._session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("get_page failed for %s: %s", url, exc)
            return f"Error fetching page: {exc}"

        if _BS4_AVAILABLE:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n")
        else:
            text = re.sub(r"<[^>]+>", " ", resp.text)

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def open_in_browser(self, url: str) -> bool:
        """Open *url* in the system's default web browser.

        Returns:
            True if the browser was opened successfully.
        """
        try:
            webbrowser.open(url)
            return True
        except Exception as exc:
            logger.error("Failed to open browser: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Weather (wttr.in — no API key required)
    # ------------------------------------------------------------------

    def get_weather(self, city: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Fetch current weather for *city* from wttr.in.

        Args:
            city: City name (e.g. "London", "New York").
            api_key: Unused; kept for API compatibility.

        Returns:
            dict with: city, condition, temperature_c, temperature_f,
            humidity, wind_kmh, feels_like_c, description.
        """
        if not _REQUESTS_AVAILABLE:
            return {"error": "requests not available"}

        encoded_city = urllib.parse.quote_plus(city)
        url = f"https://wttr.in/{encoded_city}?format=j1"

        try:
            resp = self._session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error("Weather fetch failed: %s", exc)
            return {"error": str(exc), "city": city}

        try:
            current = data["current_condition"][0]
            area = data.get("nearest_area", [{}])[0]
            area_name = area.get("areaName", [{}])[0].get("value", city)
            return {
                "city": area_name,
                "condition": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
                "temperature_c": current.get("temp_C"),
                "temperature_f": current.get("temp_F"),
                "humidity": current.get("humidity"),
                "wind_kmh": current.get("windspeedKmph"),
                "feels_like_c": current.get("FeelsLikeC"),
                "feels_like_f": current.get("FeelsLikeF"),
                "visibility_km": current.get("visibility"),
                "uv_index": current.get("uvIndex"),
            }
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Weather parse error: %s", exc)
            return {"error": "Failed to parse weather data", "city": city}

    # ------------------------------------------------------------------
    # News (public RSS feeds)
    # ------------------------------------------------------------------

    def get_news(self, topic: str = "technology", count: int = 5) -> List[Dict[str, str]]:
        """Fetch headlines from a public RSS feed for *topic*.

        Args:
            topic: Category — "technology", "science", "business",
                   "general", "world", "sports", "health", "entertainment".
            count: Maximum number of items to return.

        Returns:
            List of dicts: {title, url, summary, published}.
        """
        if not _REQUESTS_AVAILABLE or not _BS4_AVAILABLE:
            return [{"title": "Unavailable", "url": "", "summary": "Packages not installed", "published": ""}]

        feed_url = _NEWS_RSS.get(topic.lower(), _NEWS_RSS["general"])
        try:
            resp = self._session.get(feed_url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("News fetch failed: %s", exc)
            return [{"title": "Error", "url": "", "summary": str(exc), "published": ""}]

        soup = BeautifulSoup(resp.content, "xml")
        items = soup.find_all("item")[:count]

        results: List[Dict[str, str]] = []
        for item in items:
            title = item.find("title")
            link = item.find("link")
            description = item.find("description")
            pub_date = item.find("pubDate")
            results.append(
                {
                    "title": html.unescape(title.text.strip()) if title else "",
                    "url": link.text.strip() if link else "",
                    "summary": html.unescape(
                        re.sub(r"<[^>]+>", "", description.text).strip()[:300]
                    ) if description else "",
                    "published": pub_date.text.strip() if pub_date else "",
                }
            )
        return results

    # ------------------------------------------------------------------
    # Page summarisation
    # ------------------------------------------------------------------

    def summarize_page(self, url: str, max_sentences: int = 5) -> Dict[str, str]:
        """Fetch a page and return a basic extractive summary.

        Args:
            url: URL to summarise.
            max_sentences: Maximum sentences in the summary.

        Returns:
            dict with: url, title, summary.
        """
        if not _BS4_AVAILABLE or not _REQUESTS_AVAILABLE:
            return {"url": url, "title": "", "summary": "BeautifulSoup/requests not available"}

        try:
            resp = self._session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as exc:
            return {"url": url, "title": "", "summary": f"Error: {exc}"}

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.text.strip() if title_tag else ""

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        # Collect paragraph text
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 60]
        full_text = " ".join(paragraphs)

        # Sentence tokenisation (simple split)
        sentences = re.split(r"(?<=[.!?])\s+", full_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 40]

        summary = " ".join(sentences[:max_sentences])
        summary = textwrap.shorten(summary, width=1000, placeholder="...")

        return {"url": url, "title": title, "summary": summary}

    # ------------------------------------------------------------------
    # Internal parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_ddg(soup: "BeautifulSoup") -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        for result in soup.select(".result"):
            title_tag = result.select_one(".result__title")
            url_tag = result.select_one(".result__url")
            snippet_tag = result.select_one(".result__snippet")
            title = title_tag.get_text(strip=True) if title_tag else ""
            url = url_tag.get_text(strip=True) if url_tag else ""
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            if title:
                results.append({"title": title, "url": url, "snippet": snippet})
        return results[:10]

    @staticmethod
    def _parse_google(soup: "BeautifulSoup") -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        for div in soup.select("div.g"):
            title_tag = div.select_one("h3")
            link_tag = div.select_one("a")
            snippet_div = div.select_one("div.VwiC3b")
            title = title_tag.get_text(strip=True) if title_tag else ""
            url = link_tag.get("href", "") if link_tag else ""
            snippet = snippet_div.get_text(strip=True) if snippet_div else ""
            if title and url.startswith("http"):
                results.append({"title": title, "url": url, "snippet": snippet})
        return results[:10]

    @staticmethod
    def _parse_bing(soup: "BeautifulSoup") -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        for li in soup.select("li.b_algo"):
            title_tag = li.select_one("h2 a")
            snippet_tag = li.select_one("div.b_caption p")
            title = title_tag.get_text(strip=True) if title_tag else ""
            url = title_tag.get("href", "") if title_tag else ""
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            if title:
                results.append({"title": title, "url": url, "snippet": snippet})
        return results[:10]
