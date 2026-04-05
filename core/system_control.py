"""
System Control - Full OS-level control for Jarvis AI.
"""

import logging
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import psutil

from utils.config import Config

logger = logging.getLogger(__name__)

SYSTEM = platform.system()  # "Windows", "Darwin", "Linux"


class SystemControl:
    """Provides file system, process, network, and hardware control."""

    def __init__(self, config: Config):
        self.config = config

    # ------------------------------------------------------------------
    # Hardware Monitoring
    # ------------------------------------------------------------------

    def get_system_status(self) -> Dict:
        """Return a comprehensive snapshot of hardware metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        status = {
            "cpu_percent": cpu_percent,
            "cpu_count": psutil.cpu_count(),
            "ram_total_gb": round(mem.total / 1e9, 2),
            "ram_used_gb": round(mem.used / 1e9, 2),
            "ram_percent": mem.percent,
            "disk_total_gb": round(disk.total / 1e9, 2),
            "disk_used_gb": round(disk.used / 1e9, 2),
            "disk_percent": disk.percent,
            "platform": SYSTEM,
            "timestamp": datetime.now().isoformat(),
        }

        # CPU temperature (Linux/macOS via psutil)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                key = next(iter(temps))
                status["cpu_temp_c"] = round(temps[key][0].current, 1)
        except (AttributeError, Exception):
            pass

        # Network I/O
        try:
            net = psutil.net_io_counters()
            status["net_bytes_sent"] = net.bytes_sent
            status["net_bytes_recv"] = net.bytes_recv
        except Exception:
            pass

        return status

    def get_processes(self, top_n: int = 20) -> List[Dict]:
        """Return the top-N processes sorted by CPU usage."""
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                procs.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(procs, key=lambda p: p.get("cpu_percent", 0), reverse=True)[:top_n]

    def kill_process(self, pid: int) -> bool:
        """Kill a process by PID. Returns True on success."""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=5)
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
            logger.warning(f"Could not kill PID {pid}: {e}")
            return False

    def get_network_interfaces(self) -> Dict:
        """Return active network interface details."""
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        result = {}
        for iface, addr_list in addrs.items():
            result[iface] = {
                "addresses": [{"family": str(a.family), "address": a.address} for a in addr_list],
                "is_up": stats[iface].isup if iface in stats else False,
            }
        return result

    # ------------------------------------------------------------------
    # Shell Execution
    # ------------------------------------------------------------------

    def run_command(
        self,
        command: str,
        timeout: int = 30,
        shell: bool = True,
        capture: bool = True,
    ) -> Dict:
        """Execute a shell command safely and return output."""
        logger.info(f"Executing command: {command}")
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=capture,
                text=True,
                timeout=timeout,
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "command": command,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out", "command": command}
        except Exception as e:
            return {"success": False, "error": str(e), "command": command}

    # ------------------------------------------------------------------
    # File System Operations
    # ------------------------------------------------------------------

    def create_directory(self, path: str) -> bool:
        """Create a directory (including parents)."""
        try:
            Path(path).expanduser().mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"create_directory failed: {e}")
            return False

    def delete_path(self, path: str, force: bool = False) -> bool:
        """Delete a file or directory."""
        p = Path(path).expanduser()
        try:
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                if force:
                    shutil.rmtree(p)
                else:
                    p.rmdir()
            return True
        except Exception as e:
            logger.error(f"delete_path failed for {path}: {e}")
            return False

    def move_path(self, src: str, dst: str) -> bool:
        """Move/rename a file or directory."""
        try:
            shutil.move(str(Path(src).expanduser()), str(Path(dst).expanduser()))
            return True
        except Exception as e:
            logger.error(f"move_path failed {src} -> {dst}: {e}")
            return False

    def copy_path(self, src: str, dst: str) -> bool:
        """Copy a file or directory."""
        try:
            s = Path(src).expanduser()
            d = Path(dst).expanduser()
            if s.is_dir():
                shutil.copytree(str(s), str(d))
            else:
                shutil.copy2(str(s), str(d))
            return True
        except Exception as e:
            logger.error(f"copy_path failed {src} -> {dst}: {e}")
            return False

    def list_directory(self, path: str = ".") -> List[Dict]:
        """List files in a directory with metadata."""
        result = []
        p = Path(path).expanduser()
        if not p.exists():
            return result
        for entry in sorted(p.iterdir()):
            try:
                stat = entry.stat()
                result.append(
                    {
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "path": str(entry),
                    }
                )
            except Exception:
                pass
        return result

    def search_files(self, directory: str, pattern: str) -> List[str]:
        """Recursively search for files matching a glob pattern."""
        p = Path(directory).expanduser()
        return [str(f) for f in p.rglob(pattern)]

    def read_file(self, path: str, encoding: str = "utf-8") -> Optional[str]:
        """Read a text file and return its content."""
        try:
            return Path(path).expanduser().read_text(encoding=encoding)
        except Exception as e:
            logger.error(f"read_file failed: {e}")
            return None

    def write_file(self, path: str, content: str, encoding: str = "utf-8") -> bool:
        """Write content to a text file."""
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding=encoding)
            return True
        except Exception as e:
            logger.error(f"write_file failed: {e}")
            return False

    def organize_downloads(self, downloads_dir: Optional[str] = None) -> Dict:
        """
        Auto-organize the Downloads folder by file type.
        Returns a summary of moved files.
        """
        folder = Path(downloads_dir or self.config.get("paths.downloads", "~/Downloads")).expanduser()
        if not folder.exists():
            return {"moved": 0, "error": f"Directory not found: {folder}"}

        type_map = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf"],
            "Spreadsheets": [".xls", ".xlsx", ".csv", ".ods"],
            "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
            "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
            "Archives": [".zip", ".tar", ".gz", ".rar", ".7z"],
            "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yaml", ".yml"],
            "Executables": [".exe", ".msi", ".deb", ".dmg", ".sh"],
        }

        ext_to_category = {ext: cat for cat, exts in type_map.items() for ext in exts}
        moved = 0
        errors = []

        for file_path in folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                category = ext_to_category.get(ext, "Other")
                dest_dir = folder / category
                dest_dir.mkdir(exist_ok=True)
                dest = dest_dir / file_path.name
                try:
                    shutil.move(str(file_path), str(dest))
                    moved += 1
                except Exception as e:
                    errors.append(str(e))

        return {"moved": moved, "errors": errors, "directory": str(folder)}

    # ------------------------------------------------------------------
    # Application Launcher
    # ------------------------------------------------------------------

    def open_application(self, app_name: str) -> bool:
        """Launch an application by name."""
        try:
            if SYSTEM == "Windows":
                os.startfile(app_name)  # type: ignore[attr-defined]
            elif SYSTEM == "Darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:  # Linux
                subprocess.Popen([app_name])
            return True
        except Exception as e:
            logger.error(f"Could not open {app_name}: {e}")
            return False

    def open_url(self, url: str) -> bool:
        """Open a URL in the default browser."""
        import webbrowser
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Could not open URL {url}: {e}")
            return False

    # ------------------------------------------------------------------
    # System Information
    # ------------------------------------------------------------------

    def get_os_info(self) -> Dict:
        """Return OS and platform information."""
        return {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
        }

    def get_disk_partitions(self) -> List[Dict]:
        """Return disk partitions and their usage."""
        result = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                result.append(
                    {
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / 1e9, 2),
                        "used_gb": round(usage.used / 1e9, 2),
                        "percent": usage.percent,
                    }
                )
            except (PermissionError, Exception):
                pass
        return result
