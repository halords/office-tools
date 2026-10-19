"""Resource and filesystem path resolution for development and frozen PyInstaller bundles."""

import sys
from pathlib import Path


def get_resource_path(*relative_parts: str) -> Path:
    """
    Resolve absolute path to an embedded resource.
    Works seamlessly in both local editable python development and PyInstaller bundles.
    """
    if getattr(sys, "frozen", False):
        # Running in PyInstaller bundle
        if hasattr(sys, "_MEIPASS"):
            base = Path(sys._MEIPASS).resolve()
        else:
            base = Path(sys.executable).resolve().parent
        # Check direct resources or package-nested resources
        candidate = base / "offline_toolbox" / "resources"
        if candidate.exists():
            return candidate.joinpath(*relative_parts)
        candidate_alt = base / "resources"
        if candidate_alt.exists():
            return candidate_alt.joinpath(*relative_parts)
        return candidate.joinpath(*relative_parts)
    else:
        # Development mode
        base = Path(__file__).resolve().parent.parent / "resources"
        return base.joinpath(*relative_parts)
