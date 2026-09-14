"""Neurodot modular application package."""

__version__ = "1.0.0"


def main():
    """Collect startup settings, then load and run the processing workflow."""
    from . import config
    from .startup_gui import choose_startup_settings

    startup = choose_startup_settings()
    if startup is None:
        return None

    config.apply_startup_settings(**startup)

    from .progress_gui import ProgressWindow

    progress = ProgressWindow()
    progress.show(
        status="Loading Neurodot components...",
        detail="Preparing Cellpose and the IMS processing libraries.",
    )

    # Import only after applying the selection. The behavior-preserving
    # modules intentionally snapshot config constants at import time.
    try:
        from .workflow import main as run

        return run(progress=progress)
    except Exception:
        progress.close()
        raise


__all__ = ["main", "__version__"]
