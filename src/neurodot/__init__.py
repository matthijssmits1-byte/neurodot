"""Neurodot modular application package."""

__version__ = "1.0.0"


def main():
    """Collect startup settings, then load and run the processing workflow."""
    from . import config
    from .startup_gui import choose_startup_settings

    startup = choose_startup_settings()
    if startup is None:
        return None

    use_quality_review = bool(startup.pop("use_quality_review", True))
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
        def load_workflow():
            from .workflow import main as run_workflow

            return run_workflow

        # Importing Torch, Cellpose, SciPy, and the workflow can take several
        # seconds. Keep that work off Tk's thread so the indeterminate bar and
        # window continue repainting during startup.
        run = progress.run_task(load_workflow)

        return run(
            progress=progress,
            use_quality_review=use_quality_review,
        )
    except Exception:
        progress.close()
        raise


__all__ = ["main", "__version__"]
