"""
Research Assistant - Summarize and organize research content.
"""

import logging
import re
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class ResearchAssistant:
    """
    Helps with research tasks:
    - Summarize web content / papers
    - Extract key findings
    - Manage citations
    - Build literature reviews
    """

    def __init__(self, config: Config, ai_engine=None):
        self.config = config
        self.ai_engine = ai_engine
        self._references: List[Dict] = []
        self._notes: List[Dict] = []

    # ------------------------------------------------------------------
    # Summarization
    # ------------------------------------------------------------------

    def summarize_text(self, text: str, max_words: int = 150) -> str:
        """Summarize a block of text."""
        if self.ai_engine:
            return self.ai_engine.summarize(text, max_words=max_words)
        # Fallback: extract first N sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        result = []
        words = 0
        for sentence in sentences:
            w = len(sentence.split())
            if words + w > max_words:
                break
            result.append(sentence)
            words += w
        return " ".join(result) if result else text[:500]

    def extract_key_points(self, text: str, num_points: int = 5) -> List[str]:
        """Extract the N most important sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        # Score by sentence length (longer sentences often carry more info)
        scored = [(s, len(s.split())) for s in sentences if len(s.split()) > 5]
        scored.sort(key=lambda x: -x[1])
        return [s for s, _ in scored[:num_points]]

    # ------------------------------------------------------------------
    # Citation Management
    # ------------------------------------------------------------------

    def add_reference(
        self,
        title: str,
        url: str = "",
        authors: Optional[List[str]] = None,
        year: Optional[int] = None,
        notes: str = "",
    ) -> Dict:
        """Add a reference to the library."""
        ref = {
            "id": len(self._references) + 1,
            "title": title,
            "url": url,
            "authors": authors or [],
            "year": year,
            "notes": notes,
        }
        self._references.append(ref)
        return ref

    def get_references(self) -> List[Dict]:
        return list(self._references)

    def format_citation(self, ref_id: int, style: str = "apa") -> str:
        """Format a reference as a citation string."""
        ref = next((r for r in self._references if r["id"] == ref_id), None)
        if not ref:
            return ""
        authors = ", ".join(ref.get("authors") or []) or "Unknown"
        year = ref.get("year") or "n.d."
        title = ref.get("title", "")
        url = ref.get("url", "")
        if style == "apa":
            return f"{authors} ({year}). {title}. {url}"
        elif style == "mla":
            return f"{authors}. \"{title}.\" {year}. {url}"
        return f"[{ref_id}] {title} - {authors} ({year})"

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def add_note(self, content: str, tags: Optional[List[str]] = None, source: str = "") -> Dict:
        from datetime import datetime
        note = {
            "id": len(self._notes) + 1,
            "content": content,
            "tags": tags or [],
            "source": source,
            "created_at": datetime.now().isoformat(),
        }
        self._notes.append(note)
        return note

    def search_notes(self, query: str) -> List[Dict]:
        q = query.lower()
        return [n for n in self._notes if q in n["content"].lower() or q in str(n.get("tags", "")).lower()]

    def get_notes(self) -> List[Dict]:
        return list(self._notes)

    # ------------------------------------------------------------------
    # Literature Review
    # ------------------------------------------------------------------

    def generate_literature_review(self) -> str:
        """Generate a simple literature review from saved references."""
        if not self._references:
            return "No references found. Add references using add_reference()."

        lines = ["# Literature Review\n"]
        for ref in self._references:
            lines.append(f"## {ref['title']}")
            if ref.get("authors"):
                lines.append(f"**Authors:** {', '.join(ref['authors'])}")
            if ref.get("year"):
                lines.append(f"**Year:** {ref['year']}")
            if ref.get("notes"):
                lines.append(f"**Notes:** {ref['notes']}")
            if ref.get("url"):
                lines.append(f"**Source:** {ref['url']}")
            lines.append("")
        return "\n".join(lines)
