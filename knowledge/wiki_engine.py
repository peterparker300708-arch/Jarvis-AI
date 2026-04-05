"""
Wiki Engine - Personal knowledge base for Jarvis AI.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class WikiEngine:
    """
    Personal knowledge base with:
    - Article creation and editing
    - Full-text search
    - Tag system
    - Hierarchical categories
    """

    def __init__(self, config: Config, db=None):
        self.config = config
        self.db = db
        self._articles: Dict[str, Dict] = {}
        self._tag_index: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_article(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        category: str = "General",
    ) -> Dict:
        """Create a new wiki article."""
        article_id = self._slugify(title)
        article = {
            "id": article_id,
            "title": title,
            "content": content,
            "category": category,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "word_count": len(content.split()),
        }
        self._articles[article_id] = article
        self._update_tag_index(article_id, tags or [])
        logger.info(f"Article created: {title}")
        return article

    def get_article(self, article_id: str) -> Optional[Dict]:
        return self._articles.get(article_id)

    def update_article(
        self,
        article_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        if article_id not in self._articles:
            return False
        article = self._articles[article_id]
        if title:
            article["title"] = title
        if content is not None:
            article["content"] = content
            article["word_count"] = len(content.split())
        if tags is not None:
            article["tags"] = tags
            self._update_tag_index(article_id, tags)
        article["updated_at"] = datetime.now().isoformat()
        return True

    def delete_article(self, article_id: str) -> bool:
        if article_id in self._articles:
            # Clean tag index
            for tag, ids in self._tag_index.items():
                if article_id in ids:
                    ids.remove(article_id)
            del self._articles[article_id]
            return True
        return False

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str) -> List[Dict]:
        """Full-text search over articles."""
        query_lower = query.lower()
        results = []
        for article in self._articles.values():
            if query_lower in article["title"].lower() or query_lower in article["content"].lower():
                # Simple relevance: title match > content match
                score = 2 if query_lower in article["title"].lower() else 1
                results.append({**article, "score": score})
        return sorted(results, key=lambda a: -a["score"])

    def search_by_tag(self, tag: str) -> List[Dict]:
        """Return all articles with a specific tag."""
        ids = self._tag_index.get(tag.lower(), [])
        return [self._articles[i] for i in ids if i in self._articles]

    def list_articles(self, category: Optional[str] = None) -> List[Dict]:
        """List all articles, optionally filtered by category."""
        articles = list(self._articles.values())
        if category:
            articles = [a for a in articles if a.get("category") == category]
        return sorted(articles, key=lambda a: a["updated_at"], reverse=True)

    def list_tags(self) -> List[str]:
        return sorted(k for k, v in self._tag_index.items() if v)

    def list_categories(self) -> List[str]:
        return sorted(set(a.get("category", "General") for a in self._articles.values()))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _slugify(self, title: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        base = slug.strip("-")
        # Ensure uniqueness
        if base not in self._articles:
            return base
        counter = 1
        while f"{base}-{counter}" in self._articles:
            counter += 1
        return f"{base}-{counter}"

    def _update_tag_index(self, article_id: str, tags: List[str]):
        for tag in tags:
            t = tag.lower()
            if t not in self._tag_index:
                self._tag_index[t] = []
            if article_id not in self._tag_index[t]:
                self._tag_index[t].append(article_id)

    def get_stats(self) -> Dict:
        return {
            "total_articles": len(self._articles),
            "total_tags": len(self._tag_index),
            "categories": self.list_categories(),
            "total_words": sum(a.get("word_count", 0) for a in self._articles.values()),
        }
