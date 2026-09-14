"""Filesystem locations that work from source and from a frozen application."""

from pathlib import Path
import sys


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]
LEGACY_ROOT = PROJECT_ROOT.parent
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT)).resolve()


def runtime_data_root():
    """Writable working directory for source runs or installed builds."""
    if getattr(sys, "frozen", False):
        return Path.home() / "Documents" / "Neurodot"
    return PROJECT_ROOT


RUNTIME_DATA_ROOT = runtime_data_root()


def resolve_resource(relative_path, legacy_relative_path=None):
    """Return a bundled/project resource, with a v21-workspace fallback.

    The fallback avoids duplicating the large Cellpose model and Imaris donor
    while Neurodot is developed. Packaged releases contain the resource in
    the project's ``resources`` directory and therefore never use it.
    """
    relative_path = Path(relative_path)
    project_candidate = BUNDLE_ROOT / "resources" / relative_path
    if project_candidate.exists():
        return project_candidate

    if legacy_relative_path is not None and not getattr(sys, "frozen", False):
        legacy_candidate = LEGACY_ROOT / Path(legacy_relative_path)
        if legacy_candidate.exists():
            return legacy_candidate

    return project_candidate


def executable_dir():
    """Directory containing the installed executable, or the project root."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def configure_windows_app_identity():
    """Give all Neurodot windows one explicit Windows taskbar identity."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Neurodot.AdvancedCellDetection"
        )
    except Exception:
        pass
