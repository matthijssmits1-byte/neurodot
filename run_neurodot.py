"""Development launcher; run this file directly from VS Code."""

from pathlib import Path
import sys


SOURCE_DIR = Path(__file__).resolve().parent / "src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from neurodot import main
from neurodot.logging_setup import install_file_logging, show_fatal_error


def run():
    log_path = install_file_logging()
    if "--self-test" in sys.argv:
        from neurodot.self_test import run_self_test

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
