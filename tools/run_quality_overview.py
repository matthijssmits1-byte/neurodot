"""Open only the quality-review window; never move or process files."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def main():
    from neurodot import config
    from neurodot.startup_gui import choose_startup_settings

    startup = choose_startup_settings()
    if startup is None:
        return 0
    config.apply_startup_settings(**startup)

    ims_files = sorted(config.IMS_INPUT_DIR.glob("*.ims"))
    if not ims_files:
        from tkinter import messagebox

        messagebox.showinfo(
            "No IMS files",
            f"No .ims files were found in:\n\n{config.IMS_INPUT_DIR}",
        )
        return 0

    # Import after applying startup settings because modules intentionally
    # snapshot configuration constants at import time.
    from neurodot.quality_review import preview_selection_only

    result = preview_selection_only(ims_files)
    if result is not None:
        included = len(result["included"])
        excluded = len(result["excluded"])
        print(
            f"Overview-only result: {included} included, {excluded} excluded. "
            "No files were moved."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
