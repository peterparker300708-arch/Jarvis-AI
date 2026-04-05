"""
Web Browser Module - Web monitoring, scraping, form filling for Jarvis AI.
"""

import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

from utils.config import Config

logger = logging.getLogger(__name__)


class WebBrowser:
    """
    Provides web browsing capabilities:
    - Web search
    - Page content extraction
    - Website monitoring / change detection
    - Basic form interaction (via requests + BeautifulSoup)
    - Selenium integration for JS-heavy pages
    """

    def __init__(self, config: Config):
        self.config = config
        self.user_agent = config.get(
            "scraping.user_agent",
            "Mozilla/5.0 (compatible; JarvisBot/2.0)",
        )
        self.timeout = config.get("scraping.timeout", 30)
        self.max_retries = config.get("scraping.max_retries", 3)
        self._monitored_pages: Dict[str, Dict] = {}
        self._requests_available = self._check_requests()
        self._bs4_available = self._check_bs4()

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def fetch(self, url: str) -> Optional[str]:
        """Fetch raw HTML content from a URL."""
        if not self._requests_available:
            return None
        import requests
        headers = {"User-Agent": self.user_agent}
        for attempt in range(self.max_retries):
            try:
                resp = requests.get(url, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                logger.warning(f"Fetch attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.config.get("scraping.delay_between_requests", 1.0))
        return None

    def extract_text(self, html: str) -> str:
        """Extract clean text from HTML."""
        if not self._bs4_available or not html:
            return html or ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    def extract_links(self, html: str, base_url: str = "") -> List[str]:
        """Extract all hyperlinks from HTML."""
        if not self._bs4_available:
            return []
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if base_url:
                href = urljoin(base_url, href)
            links.append(href)
        return list(set(links))

    def extract_price(self, html: str) -> Optional[str]:
        """Attempt to extract a price from a product page."""
        if not self._bs4_available:
            return None
        import re
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        # Common price patterns
        price_pattern = re.compile(r"\$\s*\d+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*USD", re.IGNORECASE)
        text = soup.get_text()
        match = price_pattern.search(text)
        return match.group(0).strip() if match else None

    # ------------------------------------------------------------------
    # Web Search
    # ------------------------------------------------------------------

    def search_web(self, query: str, num_results: int = 5) -> List[Dict]:
        """Perform a web search using DuckDuckGo (no API key required)."""
        if not self._requests_available:
            return []
        import requests
        import re
        try:
            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            html = self.fetch(url)
            if not html:
                return []
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            results = []
            for result in soup.select(".result")[:num_results]:
                title_tag = result.select_one(".result__title")
                snippet_tag = result.select_one(".result__snippet")
                link_tag = result.select_one(".result__url")
                if title_tag:
                    results.append(
                        {
                            "title": title_tag.get_text(strip=True),
                            "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                            "url": link_tag.get_text(strip=True) if link_tag else "",
                        }
                    )
            return results
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Website Monitoring
    # ------------------------------------------------------------------

    def add_monitor(self, url: str, name: str = "") -> bool:
        """Start monitoring a URL for changes."""
        html = self.fetch(url)
        if html is None:
            return False
        content = self.extract_text(html)
        self._monitored_pages[url] = {
            "name": name or url,
            "url": url,
            "content_hash": hash(content),
            "last_content": content[:500],
            "added_at": str(int(time.time())),
            "change_detected": False,
        }
        logger.info(f"Monitoring started for: {url}")
        return True

    def check_monitors(self) -> List[Dict]:
        """Check all monitored pages for changes."""
        changes = []
        for url, info in self._monitored_pages.items():
            html = self.fetch(url)
            if html:
                content = self.extract_text(html)
                new_hash = hash(content)
                if new_hash != info["content_hash"]:
                    info["change_detected"] = True
                    info["content_hash"] = new_hash
                    info["last_content"] = content[:500]
                    changes.append({"url": url, "name": info["name"], "change": True})
                else:
                    changes.append({"url": url, "name": info["name"], "change": False})
        return changes

    def get_monitors(self) -> List[Dict]:
        return [
            {
                "url": url,
                "name": info["name"],
                "change_detected": info["change_detected"],
                "added_at": info["added_at"],
            }
            for url, info in self._monitored_pages.items()
        ]

    # ------------------------------------------------------------------

    @staticmethod
    def _check_requests() -> bool:
        try:
            import requests  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_bs4() -> bool:
        try:
            import bs4  # noqa: F401
            return True
        except ImportError:
            return False
