"""Filesystem locations that work from source and from a frozen application."""

from pathlib import Path
import sys


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT)).resolve()


def runtime_data_root():
    """Writable working directory for source runs or installed builds."""
    if getattr(sys, "frozen", False):
        return Path.home() / "Documents" / "Neurodot"
    return PROJECT_ROOT


RUNTIME_DATA_ROOT = runtime_data_root()


def resolve_resource(relative_path, legacy_relative_path=None):
    """Resolve the first existing named resource, preferring the primary name.

    Both names remain inside this project's ``resources`` directory. The
    optional second name supports established assets whose filename differs
    from the current preferred filename, without falling back to an unrelated
    legacy workspace.
    """
    primary = BUNDLE_ROOT / "resources" / Path(relative_path)
    if primary.exists() or legacy_relative_path is None:
        return primary

    fallback = BUNDLE_ROOT / "resources" / Path(legacy_relative_path)
    if fallback.exists():
        return fallback
    return primary


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
