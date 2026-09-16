"""Themed preflight window for selecting a Neurodot processing job."""

from pathlib import Path
import math

from .config import (
    CELLPOSE_MODEL_PATH,
    configure_windows_app_identity,
    GUI_ACCENT,
    GUI_BANNER_PATH,
    GUI_BG,
    GUI_BORDER,
    GUI_CONTROL_ACTIVE_BG,
    GUI_CONTROL_BG,
    GUI_FG,
    GUI_ICON_ICO_PATH,
    GUI_ICON_PATH,
    GUI_MUTED_FG,
    GUI_PANEL_BG,
    IMS_INPUT_DIR,
    NATIVE_CELLPPOSE_MODEL,
    OUTPUT_FILE_TAG,
    OUTPUT_SCENE_DIR,
    PREDICTED_SPOT_DIAMETER_UM,
)


class StartupWindow:
    """Small configuration dialog displayed before Cellpose is imported."""

    def __init__(self):
        import tkinter as tk
        from tkinter import filedialog, messagebox

        self.tk = tk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.result = None
        self._images = []

        # Ensure the packaged application's writable defaults exist before the
        # input-folder validator is used. Source runs already contain these
        # directories, so this is harmless there.
        IMS_INPUT_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_SCENE_DIR.mkdir(parents=True, exist_ok=True)

        configure_windows_app_identity()
        self.root = tk.Tk()
        # Keep the native white Tk surface off-screen until the complete dark
        # interface has been constructed.
        self.root.withdraw()
        self.root.title("Neurodot | Start a counting job")
        self.root.configure(bg=GUI_BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._cancel)

        self.input_var = tk.StringVar(value=str(IMS_INPUT_DIR))
        self.output_var = tk.StringVar(value=str(OUTPUT_SCENE_DIR))
        self.tag_var = tk.StringVar(value=OUTPUT_FILE_TAG)
        self.spot_diameter_var = tk.StringVar(
            value=f"{PREDICTED_SPOT_DIAMETER_UM:g}"
        )
        self.model_var = tk.StringVar(value=str(CELLPOSE_MODEL_PATH))
        self.model_mode = tk.StringVar(
            value=(
                "local"
                if CELLPOSE_MODEL_PATH and Path(CELLPOSE_MODEL_PATH).is_file()
                else "builtin"
            )
        )
        self.preview_var = tk.StringVar()

        self._set_icon()
        self._build()
        self.tag_var.trace_add("write", lambda *_: self._update_preview())
        self._update_preview()
        self._refresh_model_buttons()
        self._centre_window()

    def _set_icon(self):
        if GUI_ICON_ICO_PATH.is_file():
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

        outer = tk.Frame(self.root, bg=GUI_BG, padx=22, pady=20)
        outer.pack(fill="both", expand=True)

        content = tk.Frame(outer, bg=GUI_BG)
        content.pack(fill="both", expand=True)
        self.content_frame = content

        form = tk.Frame(content, bg=GUI_BG)
        form.grid(row=0, column=0, sticky="nsew")

        tk.Label(
            form,
            text="START A COUNTING JOB",
            bg=GUI_BG,
            fg=GUI_ACCENT,
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 3))

        tk.Label(
            form,
            text="Choose the files and model for this run, then select how to begin.",
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 17))

        self._path_row(form, 2, "INPUT FOLDER", self.input_var, self._browse_input)
        self._path_row(form, 4, "OUTPUT FOLDER", self.output_var, self._browse_output)

        tk.Label(
            form,
            text="OUTPUT FILE TAG",
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI Semibold", 8),
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(13, 5))

        self._entry(form, self.tag_var).grid(
            row=7, column=0, columnspan=3, sticky="ew"
        )
        tk.Label(
            form,
            textvariable=self.preview_var,
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI", 8),
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(4, 0))

        tk.Label(
            form,
            text="OUTPUT SPOT DIAMETER (µm)",
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI Semibold", 8),
        ).grid(row=9, column=0, columnspan=3, sticky="w", pady=(16, 6))

        self._entry(form, self.spot_diameter_var).grid(
            row=10, column=0, columnspan=3, sticky="ew"
        )
        tk.Label(
            form,
            text="Imaris Spot size only; cell detection is unchanged. Default: 5.0 µm.",
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI", 8),
        ).grid(row=11, column=0, columnspan=3, sticky="w", pady=(4, 0))

        tk.Label(
            form,
            text="CELLPOSE MODEL",
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI Semibold", 8),
        ).grid(row=12, column=0, columnspan=3, sticky="w", pady=(16, 6))

        model_toggles = tk.Frame(form, bg=GUI_BG)
        model_toggles.grid(row=13, column=0, columnspan=3, sticky="w")
        self.local_model_button = self._button(
            model_toggles,
            "Local model file",
            lambda: self._set_model_mode("local"),
            width=17,
        )
        self.local_model_button.pack(side="left")
        self.builtin_model_button = self._button(
            model_toggles,
            f"Built-in {NATIVE_CELLPPOSE_MODEL}",
            lambda: self._set_model_mode("builtin"),
            width=18,
        )
        self.builtin_model_button.pack(side="left", padx=(5, 0))

        model_row = tk.Frame(form, bg=GUI_BG)
        model_row.grid(row=14, column=0, columnspan=3, sticky="ew", pady=(7, 0))
        model_row.grid_columnconfigure(0, weight=1)
        self.model_entry = self._entry(model_row, self.model_var)
        self.model_entry.grid(row=0, column=0, sticky="ew")
        self.model_browse_button = self._button(
            model_row, "Browse", self._browse_model, width=9
        )
        self.model_browse_button.grid(row=0, column=1, padx=(7, 0))

        form.grid_columnconfigure(0, weight=1)

        branding = tk.Frame(content, bg=GUI_BG, padx=0, pady=0)
        branding.grid(row=0, column=1, sticky="ns", padx=(24, 0))
        self.branding_frame = branding
        self._add_branding(branding)

        separator = tk.Frame(outer, bg=GUI_BORDER, height=1)
        separator.pack(fill="x", pady=(20, 14))

        actions = tk.Frame(outer, bg=GUI_BG)
        actions.pack(fill="x")
        tk.Label(
            actions,
            text="Image QC opens the overview first. Continue goes directly to setup.",
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI", 8),
        ).pack(side="left")
        self._button(actions, "Cancel", self._cancel, width=11).pack(side="right")
        self._button(
            actions,
            "Continue",
            lambda: self._continue(use_quality_review=False),
            width=14,
        ).pack(side="right", padx=(0, 8))
        self._button(
            actions,
            "Continue with image QC",
            lambda: self._continue(use_quality_review=True),
            width=23,
            accent=True,
        ).pack(side="right", padx=(0, 8))

    def _path_row(self, parent, row, label, variable, command):
        tk = self.tk
        tk.Label(
            parent,
            text=label,
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI Semibold", 8),
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 5))

        entry = self._entry(parent, variable)
        entry.grid(row=row + 1, column=0, columnspan=2, sticky="ew")
        self._button(parent, "Browse", command, width=9).grid(
            row=row + 1, column=2, padx=(7, 0)
        )

    def _entry(self, parent, variable):
        return self.tk.Entry(
            parent,
            textvariable=variable,
            bg=GUI_CONTROL_BG,
            fg=GUI_FG,
            insertbackground=GUI_FG,
            selectbackground=GUI_CONTROL_ACTIVE_BG,
            selectforeground=GUI_FG,
            relief="flat",
            highlightthickness=1,
            highlightbackground=GUI_BORDER,
            highlightcolor=GUI_ACCENT,
            font=("Segoe UI", 9),
            width=55,
        )

    def _button(self, parent, text, command, width, accent=False):
        return self.tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=GUI_CONTROL_BG,
            activebackground=GUI_CONTROL_ACTIVE_BG,
            fg=GUI_FG,
            activeforeground=GUI_FG,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=GUI_ACCENT if accent else GUI_BORDER,
            highlightcolor=GUI_ACCENT,
            font=("Segoe UI Semibold", 9),
            cursor="hand2",
            padx=6,
            pady=5,
        )

    def _add_branding(self, parent):
        try:
            from PIL import Image, ImageTk

            image = Image.open(GUI_BANNER_PATH).convert("RGBA")

            # The source artwork is square and contains a generous black
            # border. Crop only that near-black border so the logo itself fits
            # the startup window tightly without altering the source asset.
            luminance = image.convert("RGB").convert("L")
            visible = luminance.point(lambda value: 255 if value > 10 else 0)
            bounds = visible.getbbox()
            if bounds is not None:
                image = image.crop(bounds)

            image.thumbnail((205, 285), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image, master=self.root)
            label = self.tk.Label(
                parent,
                image=photo,
                bg=GUI_BG,
                borderwidth=0,
                highlightthickness=0,
                padx=0,
                pady=0,
            )
            label.pack(expand=True)
            self.branding_label = label
            self._images.append(photo)
        except Exception:
            label = self.tk.Label(
                parent,
                text="NEURODOT",
                bg=GUI_BG,
                fg=GUI_ACCENT,
                font=("Segoe UI Semibold", 18),
                padx=24,
                pady=80,
            )
            label.pack(expand=True)
            self.branding_label = label

    def _browse_input(self):
        selected = self.filedialog.askdirectory(
            title="Select folder containing Imaris files",
            initialdir=self._valid_initial_dir(self.input_var.get()),
        )
        if selected:
            self.input_var.set(selected)

    def _browse_output(self):
        selected = self.filedialog.askdirectory(
            title="Select output folder",
            initialdir=self._valid_initial_dir(self.output_var.get()),
        )
        if selected:
            self.output_var.set(selected)

    def _browse_model(self):
        initial = Path(self.model_var.get()).expanduser()
        selected = self.filedialog.askopenfilename(
            title="Select a Cellpose model",
            initialdir=str(initial.parent if initial.parent.is_dir() else Path.cwd()),
            filetypes=(("All model files", "*"),),
        )
        if selected:
            self.model_var.set(selected)
            self._set_model_mode("local")

    @staticmethod
    def _valid_initial_dir(value):
        candidate = Path(value).expanduser()
        if candidate.is_dir():
            return str(candidate)
        if candidate.parent.is_dir():
            return str(candidate.parent)
        return str(Path.cwd())

    def _set_model_mode(self, mode):
        self.model_mode.set(mode)
        self._refresh_model_buttons()

    def _refresh_model_buttons(self):
        local = self.model_mode.get() == "local"
        for button, selected in (
            (self.local_model_button, local),
            (self.builtin_model_button, not local),
        ):
            button.configure(
                highlightbackground=GUI_ACCENT if selected else GUI_BORDER,
                fg=GUI_FG if selected else GUI_MUTED_FG,
            )
        state = "normal" if local else "disabled"
        self.model_entry.configure(state=state)
        self.model_browse_button.configure(state=state)

    def _update_preview(self):
        tag = self.tag_var.get()
        self.preview_var.set(f"Example: image{tag}_L.ims  /  image{tag}_R.ims")

    def _continue(self, use_quality_review=True):
        input_text = self.input_var.get().strip()
        output_text = self.output_var.get().strip()
        tag = self.tag_var.get().strip()
        spot_diameter_text = self.spot_diameter_var.get().strip().replace(",", ".")

        if not input_text:
            self.messagebox.showerror("Input folder required", "Choose an input folder.")
            return
        input_dir = Path(input_text).expanduser()
        if not input_dir.is_dir():
            self.messagebox.showerror(
                "Input folder not found",
                f"The selected input folder does not exist:\n\n{input_dir}",
            )
            return
        if not output_text:
            self.messagebox.showerror("Output folder required", "Choose an output folder.")
            return
        if any(character in tag for character in '<>:"/\\|?*'):
            self.messagebox.showerror(
                "Invalid output tag",
                "The output tag contains a character Windows cannot use in a filename.",
            )
            return

        try:
            spot_diameter_um = float(spot_diameter_text)
        except ValueError:
            spot_diameter_um = float("nan")
        if not math.isfinite(spot_diameter_um) or spot_diameter_um <= 0.0:
            self.messagebox.showerror(
                "Invalid Spot diameter",
                "Enter a Spot diameter greater than zero, in micrometres.\n\n"
                "The standard value is 5.0 µm (a 2.5 µm radius).",
            )
            return

        model_path = None
        if self.model_mode.get() == "local":
            model_text = self.model_var.get().strip()
            model = Path(model_text).expanduser()
            if not model.is_file():
                self.messagebox.showerror(
                    "Cellpose model not found",
                    f"The selected model file does not exist:\n\n{model}",
                )
                return
            model_path = str(model.resolve())

        self.result = {
            "input_dir": str(input_dir.resolve()),
            "output_dir": str(Path(output_text).expanduser().resolve()),
            "output_file_tag": tag,
            "model_path": model_path,
            "spot_diameter_um": spot_diameter_um,
            "use_quality_review": bool(use_quality_review),
        }
        self.root.destroy()

    def _cancel(self):
        self.result = None
        self.root.destroy()

    def _centre_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def show(self):
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.mainloop()
        return self.result


def choose_startup_settings():
    """Display the preflight dialog and return selections, or None on cancel."""
    return StartupWindow().show()


__all__ = ["StartupWindow", "choose_startup_settings"]
