"""
PDF Manager - Create, merge, split, and extract text from PDFs.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class PDFManager:
    """
    PDF operations:
    - Text extraction
    - PDF creation (from text)
    - Merge multiple PDFs
    - Split a PDF into pages
    - Convert text files to PDF
    """

    def __init__(self, config: Config):
        self.config = config
        self.pdf_dir = Path(config.get("paths.pdfs", "~/Documents/PDFs")).expanduser()
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self._pypdf_available = self._check_pypdf()
        self._reportlab_available = self._check_reportlab()

    # ------------------------------------------------------------------
    # Text Extraction
    # ------------------------------------------------------------------

    def extract_text(self, pdf_path: str) -> Optional[str]:
        """Extract plain text from a PDF file."""
        if not self._pypdf_available:
            return None
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return None

    def get_page_count(self, pdf_path: str) -> int:
        """Return the number of pages in a PDF."""
        if not self._pypdf_available:
            return 0
        try:
            import pypdf
            return len(pypdf.PdfReader(pdf_path).pages)
        except Exception as e:
            logger.error(f"get_page_count failed: {e}")
            return 0

    # ------------------------------------------------------------------
    # Merge / Split
    # ------------------------------------------------------------------

    def merge(self, input_paths: List[str], output_path: str) -> bool:
        """Merge multiple PDF files into one."""
        if not self._pypdf_available:
            return False
        try:
            import pypdf
            writer = pypdf.PdfWriter()
            for path in input_paths:
                reader = pypdf.PdfReader(path)
                for page in reader.pages:
                    writer.add_page(page)
            with open(output_path, "wb") as f:
                writer.write(f)
            logger.info(f"PDFs merged into: {output_path}")
            return True
        except Exception as e:
            logger.error(f"PDF merge failed: {e}")
            return False

    def split(self, pdf_path: str, output_dir: str) -> List[str]:
        """Split a PDF into individual pages."""
        if not self._pypdf_available:
            return []
        output_files = []
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            os.makedirs(output_dir, exist_ok=True)
            base_name = Path(pdf_path).stem
            for i, page in enumerate(reader.pages):
                writer = pypdf.PdfWriter()
                writer.add_page(page)
                out_path = os.path.join(output_dir, f"{base_name}_page_{i + 1}.pdf")
                with open(out_path, "wb") as f:
                    writer.write(f)
                output_files.append(out_path)
            logger.info(f"PDF split into {len(output_files)} pages")
        except Exception as e:
            logger.error(f"PDF split failed: {e}")
        return output_files

    def extract_pages(self, pdf_path: str, pages: List[int], output_path: str) -> bool:
        """Extract specific pages (0-indexed) from a PDF."""
        if not self._pypdf_available:
            return False
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            writer = pypdf.PdfWriter()
            for page_num in pages:
                if 0 <= page_num < len(reader.pages):
                    writer.add_page(reader.pages[page_num])
            with open(output_path, "wb") as f:
                writer.write(f)
            return True
        except Exception as e:
            logger.error(f"extract_pages failed: {e}")
            return False

    # ------------------------------------------------------------------
    # PDF Creation
    # ------------------------------------------------------------------

    def create_from_text(self, text: str, output_path: str, title: str = "") -> bool:
        """Create a PDF from plain text using ReportLab."""
        if not self._reportlab_available:
            logger.warning("ReportLab not available — cannot create PDF")
            return False
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet

            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            if title:
                story.append(Paragraph(title, styles["Title"]))
                story.append(Spacer(1, 12))
            for line in text.split("\n"):
                if line.strip():
                    story.append(Paragraph(line, styles["Normal"]))
                else:
                    story.append(Spacer(1, 6))
            doc.build(story)
            logger.info(f"PDF created: {output_path}")
            return True
        except Exception as e:
            logger.error(f"create_from_text failed: {e}")
            return False

    # ------------------------------------------------------------------

    @staticmethod
    def _check_pypdf() -> bool:
        try:
            import pypdf  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_reportlab() -> bool:
        try:
            import reportlab  # noqa: F401
            return True
        except ImportError:
            return False
