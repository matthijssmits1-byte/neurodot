"""Small themed progress window for console-free Neurodot builds."""

from pathlib import Path
import os
import queue
import threading

from .config import (
    GUI_ACCENT,
    GUI_BG,
    GUI_BORDER,
    GUI_CONTROL_ACTIVE_BG,
    GUI_CONTROL_BG,
    GUI_FG,
    GUI_ICON_ICO_PATH,
    GUI_ICON_PATH,
    GUI_MUTED_FG,
    configure_windows_app_identity,
)


class ProgressWindow:
    """Keep users informed while the main annotation GUI is not visible."""

    def __init__(self):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self._images = []
        self.output_dir = None
        self.finished = False
        self._ui_thread_id = threading.get_ident()
        self._events = queue.Queue()

        configure_windows_app_identity()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Neurodot | Processing")
        self.root.configure(bg=GUI_BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._ignore_close)
        self._set_icon()
        self._build()
        self._centre_window()

    def _set_icon(self):
        if Path(GUI_ICON_ICO_PATH).is_file():
            try:
                self.root.iconbitmap(str(GUI_ICON_ICO_PATH))
                self.root.iconbitmap(default=str(GUI_ICON_ICO_PATH))
            except Exception:
                pass
        try:
            icon = self.tk.PhotoImage(master=self.root, file=str(GUI_ICON_PATH))
            self.root.iconphoto(False, icon)
            self.root.iconphoto(True, icon)
            self._images.append(icon)
        except Exception:
            pass

    def _build(self):
        tk = self.tk
        ttk = self.ttk

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Neurodot.Horizontal.TProgressbar",
            troughcolor=GUI_CONTROL_BG,
            background=GUI_ACCENT,
            bordercolor=GUI_BORDER,
            lightcolor=GUI_ACCENT,
            darkcolor=GUI_ACCENT,
        )

        outer = tk.Frame(self.root, bg=GUI_BG, padx=24, pady=22)
        outer.pack(fill="both", expand=True)

        self.heading_var = tk.StringVar(value="PREPARING NEURODOT")
        tk.Label(
            outer,
            textvariable=self.heading_var,
            bg=GUI_BG,
            fg=GUI_ACCENT,
            font=("Segoe UI Semibold", 13),
        ).pack(anchor="w")

        self.status_var = tk.StringVar(value="Starting...")
        tk.Label(
            outer,
            textvariable=self.status_var,
            bg=GUI_BG,
            fg=GUI_FG,
            font=("Segoe UI Semibold", 10),
            anchor="w",
        ).pack(fill="x", pady=(17, 3))

        self.detail_var = tk.StringVar(value="")
        tk.Label(
            outer,
            textvariable=self.detail_var,
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=520,
        ).pack(fill="x", pady=(0, 13))

        self.progress = ttk.Progressbar(
            outer,
            mode="indeterminate",
            style="Neurodot.Horizontal.TProgressbar",
            length=520,
        )
        self.progress.pack(fill="x")

        self.button_row = tk.Frame(outer, bg=GUI_BG)
        self.button_row.pack(fill="x", pady=(18, 0))

        self.open_button = tk.Button(
            self.button_row,
            text="Open output folder",
            command=self._open_output,
            bg=GUI_CONTROL_BG,
            fg=GUI_FG,
            activebackground=GUI_CONTROL_ACTIVE_BG,
            activeforeground=GUI_FG,
            relief="flat",
            bd=0,
            padx=16,
            pady=7,
            font=("Segoe UI", 9),
        )
        self.close_button = tk.Button(
            self.button_row,
            text="Close",
            command=self.close,
            bg=GUI_CONTROL_BG,
            fg=GUI_FG,
            activebackground=GUI_CONTROL_ACTIVE_BG,
            activeforeground=GUI_FG,
            relief="flat",
            bd=0,
            padx=22,
            pady=7,
            font=("Segoe UI", 9),
        )

    def _centre_window(self):
        self.root.update_idletasks()
        width = max(570, self.root.winfo_reqwidth())
        height = max(225, self.root.winfo_reqheight())
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _ignore_close(self):
        if self.finished:
            self.close()
        else:
            self.root.bell()

    def show(self, status=None, detail=None, heading=None):
        if heading is not None:
            self.heading_var.set(str(heading))
        if status is not None:
            self.status_var.set(str(status))
        if detail is not None:
            self.detail_var.set(str(detail))
        self.root.deiconify()
        self.root.lift()
        if str(self.progress.cget("mode")) == "indeterminate":
            self.progress.start(12)
        self._refresh()

    def hide(self):
        self.progress.stop()
        self.root.withdraw()
        self._refresh()

    def update(self, status, detail="", current=None, total=None, heading=None):
        if threading.get_ident() != self._ui_thread_id:
            self._events.put((
                "update",
                (status, detail, current, total, heading),
            ))
            return
        self._apply_update(status, detail, current, total, heading)

    def _apply_update(self, status, detail, current, total, heading):
        if heading is not None:
            self.heading_var.set(str(heading))
        self.status_var.set(str(status))
        self.detail_var.set(str(detail))
        if current is not None and total:
            self.progress.stop()
            self.progress.configure(mode="determinate", maximum=max(1, int(total)))
            self.progress["value"] = min(int(current), int(total))
        elif str(self.progress.cget("mode")) != "indeterminate":
            self.progress.configure(mode="indeterminate")
            self.progress.start(12)
        self._refresh()

    def run_task(self, function):
        """Run expensive work while Tk continues painting and animating."""
        result = {}
        task_done = {"value": False}

        def worker():
            try:
                result["value"] = function()
            except BaseException as exc:
                result["error"] = exc
            finally:
                self._events.put(("done", None))

        def poll_events():
            while True:
                try:
                    event, payload = self._events.get_nowait()
                except queue.Empty:
                    break
                if event == "update":
                    self._apply_update(*payload)
                elif event == "done":
                    task_done["value"] = True

            if task_done["value"]:
                self.root.quit()
            else:
                self.root.after(50, poll_events)

        thread = threading.Thread(
            target=worker,
            name="neurodot_processing",
            daemon=False,
        )
        thread.start()
        self.root.after(20, poll_events)
        self.root.mainloop()
        thread.join()

        if "error" in result:
            raise result["error"]
        return result.get("value")

    def finish(self, success, status, detail, output_dir=None):
        self.finished = True
        self.output_dir = Path(output_dir) if output_dir else None
        self.progress.stop()
        self.progress.configure(mode="determinate", maximum=1, value=1)
        self.heading_var.set("COUNTING COMPLETE" if success else "COUNTING FINISHED WITH ERRORS")
        self.status_var.set(str(status))
        self.detail_var.set(str(detail))
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        if self.output_dir is not None:
            self.open_button.pack(side="left")
        self.close_button.pack(side="right")
        # The window was initially sized while this row was empty. Recalculate
        # after revealing the completion actions so wrapped paths cannot force
        # the buttons below the fixed client area and clip them vertically.
        self._centre_window()
        self.show()
        self.root.mainloop()

    def _open_output(self):
        if self.output_dir is None:
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(self.output_dir))
        except Exception:
            self.root.bell()

    def _refresh(self):
        try:
            self.root.update_idletasks()
            self.root.update()
        except self.tk.TclError:
            pass

    def close(self):
        try:
            self.progress.stop()
            self.root.quit()
            self.root.destroy()
        except self.tk.TclError:
            pass


__all__ = ["ProgressWindow"]
