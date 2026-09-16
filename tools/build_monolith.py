"""Generate the optional self-contained Neurodot script."""

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "src" / "neurodot"
OUTPUT_PATH = PROJECT_ROOT / "Neurodot.py"

MODULE_ORDER = (
    "paths.py",
    "config.py",
    "common.py",
    "imaris_io.py",
    "image_io.py",
    "detection.py",
    "geometry.py",
    "logging_setup.py",
    "startup_gui.py",
    "progress_gui.py",
    "qc_io.py",
    "quality_review.py",
    "gui.py",
    "self_test.py",
    "workflow.py",
)

HEAVY_IMPORTS = {
    "import numpy as np",
    "import h5py",
    "import scipy.ndimage as ndi",
    "import torch",
    "import torch.nn as nn",
    "from cellpose import models, transforms",
}


def prepare_module(module_name):
    """Remove package boundaries while retaining the module implementation."""
    source = (PACKAGE_ROOT / module_name).read_text(encoding="utf-8")
    lines = source.splitlines()
    output = []
    skipping_relative_import = False

    for line in lines:
        stripped = line.strip()

        if skipping_relative_import:
            if stripped.endswith(")"):
                skipping_relative_import = False
            continue

        if re.match(r"^from\s+\.", stripped):
            if stripped.endswith("("):
                skipping_relative_import = True
            continue

        if stripped in HEAVY_IMPORTS:
            continue

        if stripped.startswith("__all__ ="):
            continue

        output.append(line)

    prepared = "\n".join(output).strip() + "\n"

    if module_name == "paths.py":
        prepared = prepared.replace(
            "PACKAGE_DIR = Path(__file__).resolve().parent\n"
            "PROJECT_ROOT = PACKAGE_DIR.parents[1]",
            "PACKAGE_DIR = Path(__file__).resolve().parent\n"
            "PROJECT_ROOT = PACKAGE_DIR",
        )

    if module_name == "workflow.py":
        prepared = prepared.replace(
            "def main(\n    progress=None,",
            "def run_workflow(\n    progress=None,",
            1,
        )

    return prepared


def render_monolith():
    """Return the complete generated script without writing it."""
    sections = [
        "#!/usr/bin/env python\n",
        '"""Neurodot: optional self-contained version of the modular app.\n\n'
        "Generated from src/neurodot by tools/build_monolith.py.\n"
        "Edit the modular source, then regenerate this file.\n"
        '"""\n',
        "# This file intentionally contains the complete application.\n"
        "# The modular source remains the maintained source of truth.\n",
    ]

    for module_name in MODULE_ORDER:
        sections.append(
            "\n\n# " + "=" * 76 + "\n"
            f"# BEGIN GENERATED MODULE: {module_name}\n"
            "# " + "=" * 76 + "\n\n"
        )
        sections.append(prepare_module(module_name))

    sections.append(
        '''

# =============================================================================
# MONOLITHIC APPLICATION ENTRY POINT
# =============================================================================

__version__ = "1.0.0"


def _load_heavy_dependencies():
    """Load the scientific stack only after the startup window is accepted."""
    global np, h5py, ndi, torch, nn, models, transforms

    import numpy as np_module
    import h5py as h5py_module
    import scipy.ndimage as ndi_module
    import torch as torch_module
    import torch.nn as nn_module
    from cellpose import models as models_module, transforms as transforms_module

    np = np_module
    h5py = h5py_module
    ndi = ndi_module
    torch = torch_module
    nn = nn_module
    models = models_module
    transforms = transforms_module


def _load_qc_dependencies():
    """Load only the numerical and HDF5 libraries required by image QC."""
    global np, h5py

    import numpy as np_module
    import h5py as h5py_module

    np = np_module
    h5py = h5py_module


def _start_daemon_preparation(function):
    from concurrent.futures import Future

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
    _load_heavy_dependencies()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return initialize_models(device, progress=None)


def _run_quality_review_first():
    _load_qc_dependencies()
    IMS_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    ims_files = sorted(IMS_INPUT_DIR.glob("*.ims"))
    donor = SCHEMA_DONOR_IMS.resolve()
    ims_files = [path for path in ims_files if path.resolve() != donor]

    if not ims_files:
        from tkinter import messagebox

        messagebox.showinfo(
            "No IMS files found",
            f"Add .ims files to:\\n\\n{IMS_INPUT_DIR.resolve()}",
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
        input_dir=IMS_INPUT_DIR,
        on_initial_previews_ready=start_preparation,
    )
    if selected_files is None:
        return None

    start_preparation()
    future = preparation["future"]
    progress = ProgressWindow()
    progress.show(
        status="Preparing Cellpose...",
        detail="Finishing the background preparation started during image QC.",
        heading="PREPARING CELL COUNTING",
    )
    try:
        loaded_models = (
            future.result()
            if future.done()
            else progress.run_task(future.result)
        )
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
    """Collect startup settings and run the complete workflow."""
    startup = choose_startup_settings()
    if startup is None:
        return None

    use_quality_review = bool(startup.pop("use_quality_review", True))
    apply_startup_settings(**startup)

    if use_quality_review:
        return _run_quality_review_first()

    progress = ProgressWindow()
    progress.show(
        status="Loading Neurodot components...",
        detail="Preparing Cellpose and the IMS processing libraries.",
    )
    try:
        progress.run_task(_load_heavy_dependencies)
        return run_workflow(
            progress=progress,
            use_quality_review=use_quality_review,
        )
    except Exception:
        progress.close()
        raise


def run():
    log_path = install_file_logging()
    if "--self-test" in sys.argv:
        _load_heavy_dependencies()
        report = Path.home() / "Documents" / "Neurodot" / "self_test.json"
        return 0 if run_self_test(report) else 1

    try:
        main()
        return 0
    except Exception as exc:
        show_fatal_error(exc, log_path)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
'''
    )

    monolith = "".join(sections)
    if re.search(r"^\s*from\s+\.", monolith, flags=re.MULTILINE):
        raise RuntimeError("Generated monolith still contains a relative import.")
    if "def run_workflow(" not in monolith:
        raise RuntimeError("Workflow entry point was not renamed.")

    return monolith


def build_monolith():
    """Write the current modular implementation as the monolith."""
    OUTPUT_PATH.write_text(render_monolith(), encoding="utf-8", newline="\n")
    return OUTPUT_PATH


if __name__ == "__main__":
    print(build_monolith())
