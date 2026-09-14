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
            "def main(progress=None):",
            "def run_workflow(progress=None):",
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


def main():
    """Collect startup settings and run the complete workflow."""
    startup = choose_startup_settings()
    if startup is None:
        return None

    apply_startup_settings(**startup)

    progress = ProgressWindow()
    progress.show(
        status="Loading Neurodot components...",
        detail="Preparing Cellpose and the IMS processing libraries.",
    )
    try:
        _load_heavy_dependencies()
        return run_workflow(progress=progress)
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
    if "def run_workflow(progress=None):" not in monolith:
        raise RuntimeError("Workflow entry point was not renamed.")

    return monolith


def build_monolith():
    """Write the current modular implementation as the monolith."""
    OUTPUT_PATH.write_text(render_monolith(), encoding="utf-8", newline="\n")
    return OUTPUT_PATH


if __name__ == "__main__":
    print(build_monolith())
