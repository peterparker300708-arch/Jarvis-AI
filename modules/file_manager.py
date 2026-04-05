"""File management module with metadata, search, deduplication, and archiving."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import shutil
import stat
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

_TYPE_FOLDERS: Dict[str, str] = {
    # Images
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images",
    ".gif": "Images", ".bmp": "Images", ".svg": "Images",
    ".webp": "Images", ".tiff": "Images", ".ico": "Images",
    # Videos
    ".mp4": "Videos", ".avi": "Videos", ".mkv": "Videos",
    ".mov": "Videos", ".wmv": "Videos", ".flv": "Videos",
    ".webm": "Videos",
    # Audio
    ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio",
    ".aac": "Audio", ".ogg": "Audio", ".m4a": "Audio",
    # Documents
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
    ".xls": "Documents", ".xlsx": "Documents", ".ppt": "Documents",
    ".pptx": "Documents", ".txt": "Documents", ".rtf": "Documents",
    ".odt": "Documents", ".csv": "Documents",
    # Code
    ".py": "Code", ".js": "Code", ".ts": "Code", ".html": "Code",
    ".css": "Code", ".java": "Code", ".cpp": "Code", ".c": "Code",
    ".h": "Code", ".go": "Code", ".rs": "Code", ".sh": "Code",
    ".rb": "Code", ".php": "Code", ".swift": "Code", ".kt": "Code",
    # Archives
    ".zip": "Archives", ".tar": "Archives", ".gz": "Archives",
    ".bz2": "Archives", ".rar": "Archives", ".7z": "Archives",
    # Executables
    ".exe": "Executables", ".msi": "Executables", ".dmg": "Executables",
    ".deb": "Executables", ".rpm": "Executables", ".AppImage": "Executables",
}


class FileManager:
    """Comprehensive file and directory management utilities."""

    # ------------------------------------------------------------------
    # Directory listing
    # ------------------------------------------------------------------

    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """List files and folders at *path* with metadata.

        Returns:
            List of dicts with: name, path, type, size, modified, created,
            is_hidden, extension.
        """
        directory = Path(path).expanduser().resolve()
        if not directory.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        entries: List[Dict[str, Any]] = []
        for item in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            try:
                st = item.stat()
                entries.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": st.st_size,
                        "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                        "created": datetime.fromtimestamp(st.st_ctime).isoformat(),
                        "is_hidden": item.name.startswith("."),
                        "extension": item.suffix.lower() if item.is_file() else "",
                    }
                )
            except PermissionError:
                entries.append({"name": item.name, "path": str(item), "error": "permission denied"})
        return entries

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_file(self, path: str, content: str = "") -> str:
        """Create a file at *path* with optional *content*.

        Returns:
            Absolute path of the created file.
        """
        file_path = Path(path).expanduser().resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        logger.debug("Created file: %s", file_path)
        return str(file_path)

    def create_directory(self, path: str) -> str:
        """Create a directory (including parents) at *path*.

        Returns:
            Absolute path of the created directory.
        """
        dir_path = Path(path).expanduser().resolve()
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug("Created directory: %s", dir_path)
        return str(dir_path)

    # ------------------------------------------------------------------
    # Delete / Move / Copy / Rename
    # ------------------------------------------------------------------

    def delete(self, path: str, recycle: bool = True) -> bool:
        """Delete a file or directory.

        Args:
            path: Target path.
            recycle: If True, attempt to send to system trash before permanent delete.

        Returns:
            True if deletion succeeded.
        """
        target = Path(path).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        if recycle:
            try:
                import send2trash  # type: ignore[import]
                send2trash.send2trash(str(target))
                logger.debug("Sent to trash: %s", target)
                return True
            except ImportError:
                logger.debug("send2trash not available; falling back to permanent delete.")

        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        logger.debug("Permanently deleted: %s", target)
        return True

    def move(self, src: str, dst: str) -> str:
        """Move *src* to *dst*.

        Returns:
            Destination path string.
        """
        source = Path(src).expanduser().resolve()
        destination = Path(dst).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = shutil.move(str(source), str(destination))
        logger.debug("Moved %s -> %s", source, result)
        return str(result)

    def copy(self, src: str, dst: str) -> str:
        """Copy *src* to *dst*.

        Returns:
            Destination path string.
        """
        source = Path(src).expanduser().resolve()
        destination = Path(dst).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(str(source), str(destination))
        else:
            shutil.copy2(str(source), str(destination))
        logger.debug("Copied %s -> %s", source, destination)
        return str(destination)

    def rename(self, path: str, new_name: str) -> str:
        """Rename a file or directory to *new_name* (basename only).

        Returns:
            New absolute path.
        """
        target = Path(path).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        new_path = target.parent / new_name
        target.rename(new_path)
        logger.debug("Renamed %s -> %s", target, new_path)
        return str(new_path)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, directory: str, pattern: str, recursive: bool = True) -> List[Dict[str, Any]]:
        """Search for files matching *pattern* under *directory*.

        Args:
            directory: Root directory to search.
            pattern: Glob-style pattern matched against filenames.
            recursive: If True, recurse into subdirectories.

        Returns:
            List of file metadata dicts (same shape as :meth:`list_directory` items).
        """
        root = Path(directory).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        results: List[Dict[str, Any]] = []
        walk_iter = root.rglob("*") if recursive else root.glob("*")
        for item in walk_iter:
            if fnmatch.fnmatch(item.name, pattern):
                try:
                    st = item.stat()
                    results.append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "type": "directory" if item.is_dir() else "file",
                            "size": st.st_size,
                            "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                        }
                    )
                except PermissionError:
                    pass
        return results

    # ------------------------------------------------------------------
    # File info
    # ------------------------------------------------------------------

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Return detailed metadata for a file or directory.

        Returns:
            dict with: name, path, type, size, size_human, extension,
            modified, created, accessed, permissions, is_symlink, owner.
        """
        target = Path(path).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        st = target.stat()
        return {
            "name": target.name,
            "path": str(target),
            "parent": str(target.parent),
            "type": "directory" if target.is_dir() else "file",
            "size": st.st_size,
            "size_human": self._human_size(st.st_size),
            "extension": target.suffix.lower() if target.is_file() else "",
            "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(st.st_ctime).isoformat(),
            "accessed": datetime.fromtimestamp(st.st_atime).isoformat(),
            "permissions": oct(stat.S_IMODE(st.st_mode)),
            "is_symlink": target.is_symlink(),
            "is_hidden": target.name.startswith("."),
        }

    # ------------------------------------------------------------------
    # Organization & deduplication
    # ------------------------------------------------------------------

    def organize_by_type(self, directory: str) -> Dict[str, int]:
        """Move files in *directory* into subfolders organised by extension.

        Only processes files in the top level of *directory* (non-recursive).

        Returns:
            dict mapping folder_name -> number of files moved.
        """
        root = Path(directory).expanduser().resolve()
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        moved: Dict[str, int] = {}
        for item in root.iterdir():
            if not item.is_file():
                continue
            folder_name = _TYPE_FOLDERS.get(item.suffix.lower(), "Other")
            dest_dir = root / folder_name
            dest_dir.mkdir(exist_ok=True)
            dest_path = dest_dir / item.name
            if dest_path.exists():
                dest_path = dest_dir / f"{item.stem}_{int(datetime.now().timestamp())}{item.suffix}"
            item.rename(dest_path)
            moved[folder_name] = moved.get(folder_name, 0) + 1

        logger.info("Organized %s: %s", root, moved)
        return moved

    def find_duplicates(self, directory: str) -> Dict[str, List[str]]:
        """Find duplicate files under *directory* by MD5 hash.

        Returns:
            dict mapping hash -> list of duplicate file paths (only groups
            with more than one file are included).
        """
        root = Path(directory).expanduser().resolve()
        hashes: Dict[str, List[str]] = {}
        for item in root.rglob("*"):
            if not item.is_file():
                continue
            try:
                h = self._md5(item)
                hashes.setdefault(h, []).append(str(item))
            except (PermissionError, OSError):
                continue
        return {h: paths for h, paths in hashes.items() if len(paths) > 1}

    # ------------------------------------------------------------------
    # Size calculation
    # ------------------------------------------------------------------

    def calculate_size(self, path: str) -> Dict[str, Any]:
        """Calculate the total size of a file or directory.

        Returns:
            dict with: path, total_bytes, total_human, file_count.
        """
        target = Path(path).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        if target.is_file():
            size = target.stat().st_size
            return {"path": str(target), "total_bytes": size, "total_human": self._human_size(size), "file_count": 1}

        total = 0
        count = 0
        for item in target.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                    count += 1
                except OSError:
                    pass
        return {"path": str(target), "total_bytes": total, "total_human": self._human_size(total), "file_count": count}

    # ------------------------------------------------------------------
    # Compression
    # ------------------------------------------------------------------

    def compress(self, path: str, output: Optional[str] = None) -> str:
        """Create a ZIP archive of *path*.

        Args:
            path: File or directory to compress.
            output: Destination .zip path. Defaults to <path>.zip.

        Returns:
            Path of the created archive.
        """
        source = Path(path).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        if output is None:
            archive_path = source.parent / (source.name + ".zip")
        else:
            archive_path = Path(output).expanduser().resolve()

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if source.is_file():
                zf.write(source, source.name)
            else:
                for item in source.rglob("*"):
                    zf.write(item, item.relative_to(source.parent))

        logger.debug("Compressed %s -> %s", source, archive_path)
        return str(archive_path)

    def extract(self, archive: str, output: Optional[str] = None) -> str:
        """Extract a ZIP archive.

        Args:
            archive: Path to the .zip file.
            output: Directory to extract into. Defaults to archive's parent.

        Returns:
            Path to the extraction directory.
        """
        archive_path = Path(archive).expanduser().resolve()
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive}")

        if output is None:
            dest = archive_path.parent / archive_path.stem
        else:
            dest = Path(output).expanduser().resolve()

        dest.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(dest)

        logger.debug("Extracted %s -> %s", archive_path, dest)
        return str(dest)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _md5(path: Path, chunk: int = 65536) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                data = fh.read(chunk)
                if not data:
                    break
                h.update(data)
        return h.hexdigest()

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024  # type: ignore[assignment]
        return f"{size_bytes:.1f} PB"
