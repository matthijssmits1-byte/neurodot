"""Persistent diagnostics for console-free standalone builds."""

from datetime import datetime
import os
from pathlib import Path
import sys
import traceback


class TeeStream:
    """Write application output to a UTF-8 log and an optional console."""

    def __init__(self, log_stream, console_stream=None):
        self.log_stream = log_stream
        self.console_stream = console_stream

    def write(self, text):
        text = str(text)
        self.log_stream.write(text)
        self.log_stream.flush()
        if self.console_stream is not None:
            try:
                self.console_stream.write(text)
                self.console_stream.flush()
            except Exception:
                pass
        return len(text)

    def flush(self):
        self.log_stream.flush()
        if self.console_stream is not None:
            try:
                self.console_stream.flush()
            except Exception:
                pass

    def isatty(self):
        return False


def log_directory():
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return base / "Neurodot" / "logs"


def install_file_logging():
    directory = log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "neurodot.log"
    stream = log_path.open("a", encoding="utf-8", buffering=1)
    stream.write("\n" + "=" * 72 + "\n")
    stream.write(f"Neurodot started {datetime.now().isoformat(timespec='seconds')}\n")
    stream.flush()

    sys.stdout = TeeStream(stream, getattr(sys, "__stdout__", None))
    sys.stderr = TeeStream(stream, getattr(sys, "__stderr__", None))
    return log_path


def show_fatal_error(exc, log_path):
    traceback.print_exc()
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Neurodot could not continue",
            f"{exc}\n\nA diagnostic log was written to:\n{log_path}",
            parent=root,
        )
        root.destroy()
    except Exception:
        pass


__all__ = ["install_file_logging", "log_directory", "show_fatal_error"]
