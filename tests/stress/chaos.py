"""
Chaos Injection Utilities

Tools for injecting failures during stress tests.
"""

import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional


class ChaosInjector:
    """Injects various failure conditions for testing VKG robustness."""

    def __init__(self):
        self._cleanup_tasks: List[Callable[[], None]] = []

    def cleanup(self) -> None:
        """Run all cleanup tasks."""
        for task in self._cleanup_tasks:
            try:
                task()
            except Exception:
                pass
        self._cleanup_tasks = []

    def kill_process_after(
        self,
        process_name: str,
        delay_seconds: float,
    ) -> threading.Thread:
        """
        Kill a process after delay.

        Args:
            process_name: Process name to kill (e.g., "slither")
            delay_seconds: Delay before killing

        Returns:
            Thread that will perform the kill
        """
        def killer():
            time.sleep(delay_seconds)
            try:
                # Try pkill first (Unix)
                subprocess.run(["pkill", "-f", process_name], check=False, capture_output=True)
            except FileNotFoundError:
                # Fall back to taskkill on Windows
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", f"{process_name}*"],
                        check=False,
                        capture_output=True,
                    )
                except FileNotFoundError:
                    pass

        thread = threading.Thread(target=killer, daemon=True)
        thread.start()
        return thread

    def delete_path_after(
        self,
        path: Path,
        delay_seconds: float,
    ) -> threading.Thread:
        """
        Delete a path after delay.

        Args:
            path: Path to delete
            delay_seconds: Delay before deletion

        Returns:
            Thread that will perform the deletion
        """
        def deleter():
            time.sleep(delay_seconds)
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
            except Exception:
                pass

        thread = threading.Thread(target=deleter, daemon=True)
        thread.start()
        return thread

    def corrupt_file(self, path: Path) -> None:
        """
        Corrupt a file by writing invalid content.

        Args:
            path: File to corrupt
        """
        # Save original for cleanup
        original = path.read_text() if path.exists() else ""
        self._cleanup_tasks.append(lambda p=path, o=original: p.write_text(o))

        # Write invalid content
        path.write_text("{{{{invalid json not json at all [[[")

    def corrupt_file_partial(self, path: Path) -> None:
        """
        Corrupt a file by truncating it.

        Args:
            path: File to corrupt
        """
        original = path.read_text() if path.exists() else ""
        self._cleanup_tasks.append(lambda p=path, o=original: p.write_text(o))

        # Truncate to half
        if original:
            path.write_text(original[: len(original) // 2])

    def make_readonly(self, path: Path) -> None:
        """
        Make a path read-only.

        Args:
            path: Path to make read-only
        """
        import stat

        original_mode = path.stat().st_mode
        self._cleanup_tasks.append(lambda p=path, m=original_mode: p.chmod(m))

        # Remove write permissions
        path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def create_limited_tmpdir(self, prefix: str = "vkg_stress_") -> Path:
        """
        Create a temp directory for testing.

        Args:
            prefix: Prefix for temp directory name

        Returns:
            Path to temporary directory
        """
        tmpdir = Path(tempfile.mkdtemp(prefix=prefix))
        self._cleanup_tasks.append(lambda d=tmpdir: shutil.rmtree(d, ignore_errors=True))
        return tmpdir


class TimeoutSimulator:
    """Simulates tool timeouts."""

    @staticmethod
    def create_slow_command(duration_seconds: int) -> List[str]:
        """Create a command that takes long time."""
        return ["python", "-c", f"import time; time.sleep({duration_seconds})"]

    @staticmethod
    def create_hanging_command() -> List[str]:
        """Create a command that hangs forever."""
        return ["python", "-c", "import time; time.sleep(999999)"]


class DiskFullSimulator:
    """Simulates disk full conditions."""

    def __init__(self, tmpdir: Path, limit_bytes: int = 1024):
        self.tmpdir = tmpdir
        self.limit_bytes = limit_bytes
        self._filler: Optional[Path] = None

    def fill(self) -> None:
        """Fill the disk to limit."""
        self._filler = self.tmpdir / ".filler"
        with open(self._filler, "wb") as f:
            f.write(b"x" * self.limit_bytes)

    def release(self) -> None:
        """Release filled space."""
        if self._filler and self._filler.exists():
            self._filler.unlink()
            self._filler = None


class ProcessMonitor:
    """Monitors process behavior during stress tests."""

    def __init__(self):
        self.events: List[dict] = []

    def record_event(self, event_type: str, details: str) -> None:
        """Record an event."""
        self.events.append({
            "type": event_type,
            "details": details,
            "timestamp": time.time(),
        })

    def had_crash(self) -> bool:
        """Check if any crash was recorded."""
        return any(e["type"] == "crash" for e in self.events)

    def had_hang(self, timeout_seconds: float = 30) -> bool:
        """Check if any hang was detected."""
        if len(self.events) < 2:
            return False
        start = self.events[0]["timestamp"]
        end = self.events[-1]["timestamp"]
        return (end - start) > timeout_seconds

    def get_summary(self) -> dict:
        """Get event summary."""
        return {
            "total_events": len(self.events),
            "had_crash": self.had_crash(),
            "event_types": list(set(e["type"] for e in self.events)),
        }
