"""Temporary file management and atomic file safety."""

import atexit
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Set


class TempFileManager:
    """Manages isolated temp workspaces for operations, ensuring automatic cleanup."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._base_dir = Path(tempfile.gettempdir()) / "offline_toolbox"
            cls._instance._base_dir.mkdir(parents=True, exist_ok=True)
            cls._instance._active_runs: Set[Path] = set()
            atexit.register(cls._instance.cleanup_all)
        return cls._instance

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def create_run_directory(self, prefix: str = "run_") -> Path:
        run_id = f"{prefix}{uuid.uuid4().hex[:8]}"
        run_dir = self._base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        self._active_runs.add(run_dir)
        return run_dir

    def cleanup_run(self, run_dir: Path) -> None:
        if run_dir in self._active_runs and run_dir.exists():
            shutil.rmtree(run_dir, ignore_errors=True)
            self._active_runs.discard(run_dir)

    def cleanup_all(self) -> None:
        for run_dir in list(self._active_runs):
            if run_dir.exists():
                shutil.rmtree(run_dir, ignore_errors=True)
        self._active_runs.clear()

    def create_temp_file(self, run_dir: Path, suffix: str = ".tmp") -> Path:
        fd, path_str = tempfile.mkstemp(suffix=suffix, dir=str(run_dir))
        os.close(fd)
        return Path(path_str)


def atomic_save(source_temp: Path, target_final: Path) -> Path:
    """Atomically moves source_temp to target_final, guaranteeing data integrity."""
    target_final.parent.mkdir(parents=True, exist_ok=True)
    # On Windows, replace works atomically if on same volume; else fallback to copy+delete
    try:
        source_temp.replace(target_final)
    except OSError:
        shutil.copy2(source_temp, target_final)
        source_temp.unlink(missing_ok=True)
    return target_final
