"""Neurodot modular application package."""

__version__ = "1.0.0"


def _start_daemon_preparation(function):
    """Run preparation without preventing a cancelled application from exiting."""
    from concurrent.futures import Future
    import threading

    future = Future()

    def worker():
        if not future.set_running_or_notify_cancel():
            return
        try:
            future.set_result(function())
        except BaseException as exc:
            future.set_exception(exc)

    threading.Thread(
        target=worker,
        name="neurodot_qc_preparation",
        daemon=True,
    ).start()
    return future


def _prepare_workflow_and_model():
    """Import the processing stack and construct Cellpose during image QC."""
    from .workflow import initialize_models, main as run_workflow
    from .workflow import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return run_workflow, initialize_models(device, progress=None)


def _run_quality_review_first(config):
    """Open lightweight QC first, then consume background preparation."""
    from .quality_review import choose_image_quality_overview

    config.IMS_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    ims_files = sorted(config.IMS_INPUT_DIR.glob("*.ims"))
    donor = config.SCHEMA_DONOR_IMS.resolve()
    ims_files = [path for path in ims_files if path.resolve() != donor]

    if not ims_files:
        from tkinter import messagebox

        messagebox.showinfo(
            "No IMS files found",
            f"Add .ims files to:\n\n{config.IMS_INPUT_DIR.resolve()}",
        )
        return None

    preparation = {"future": None}

    def start_preparation():
        if preparation["future"] is None:
            preparation["future"] = _start_daemon_preparation(
                _prepare_workflow_and_model
            )

    selected_files = choose_image_quality_overview(
        ims_files,
        input_dir=config.IMS_INPUT_DIR,
        on_initial_previews_ready=start_preparation,
    )
    if selected_files is None:
        return None

    start_preparation()
    future = preparation["future"]

    from .progress_gui import ProgressWindow

    progress = ProgressWindow()
    progress.show(
        status="Preparing Cellpose...",
        detail="Finishing the background preparation started during image QC.",
        heading="PREPARING CELL COUNTING",
    )
    try:
        if future.done():
            run_workflow, loaded_models = future.result()
        else:
            run_workflow, loaded_models = progress.run_task(future.result)
        return run_workflow(
            progress=progress,
            use_quality_review=False,
            preselected_ims_files=selected_files,
            preloaded_models=loaded_models,
            quality_review_completed=True,
        )
    except Exception:
        progress.close()
        raise


def main():
    """Collect startup settings, then load and run the processing workflow."""
    from . import config
    from .startup_gui import choose_startup_settings

    startup = choose_startup_settings()
    if startup is None:
        return None

    use_quality_review = bool(startup.pop("use_quality_review", True))
    config.apply_startup_settings(**startup)

    if use_quality_review:
        return _run_quality_review_first(config)

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
