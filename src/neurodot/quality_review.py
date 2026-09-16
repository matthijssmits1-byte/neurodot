"""Pre-analysis, high-resolution overview for series quality control."""

from datetime import datetime
import json
import queue

from .common import *
from .config import *
from .detection import apply_manual_exposure, suggest_setup_preview_white
from .image_io import read_qc_mip_for_file_channel


EXCLUDED_FOLDER_NAME = "excluded_from_analysis"
OVERVIEW_CHANNELS = ("g", "b", "r", "405")
OVERVIEW_ZOOM_MIN = 0.55
OVERVIEW_ZOOM_MAX = 6.0
OVERVIEW_ZOOM_STEP = 1.20
OVERVIEW_PREVIEW_MAX_SIZE = 400
OVERVIEW_FOREGROUND_WORKERS = 4
OVERVIEW_BACKGROUND_WORKERS = 2
OVERVIEW_INCLUDED_BORDER = "#2f7540"
OVERVIEW_INCLUDED_TEXT = "#69a976"
OVERVIEW_EXCLUDED_COLOR = "#ff5555"


class ImageQualityOverviewWindow:
    """Show every IMS MIP and let the operator exclude poor-quality files."""

    def __init__(self, ims_files, input_dir=None, apply_exclusions=True):
        import tkinter as tk
        from tkinter import messagebox
        from PIL import Image, ImageTk

        self.tk = tk
        self.messagebox = messagebox
        self.Image = Image
        self.ImageTk = ImageTk
        self.ims_files = [Path(path) for path in ims_files]
        self.input_dir = Path(input_dir) if input_dir is not None else Path(IMS_INPUT_DIR)
        self.apply_exclusions = bool(apply_exclusions)
        self.selected = {path: True for path in self.ims_files}
        self.current_channel = "g"
        self.zoom = 1.0
        self.result = None

        self.preview_cache = {}
        self.resized_preview_cache = {}
        self.pending = set()
        self.foreground_futures = {}
        self.background_futures = {}
        self.events = queue.Queue()
        self.foreground_executor = ThreadPoolExecutor(
            max_workers=max(
                1,
                min(OVERVIEW_FOREGROUND_WORKERS, len(self.ims_files)),
            ),
            thread_name_prefix="neurodot-qc-visible",
        )
        self.background_executor = ThreadPoolExecutor(
            max_workers=max(
                1,
                min(OVERVIEW_BACKGROUND_WORKERS, len(self.ims_files)),
            ),
            thread_name_prefix="neurodot-qc-preload",
        )
        self.photo_images = []
        self.hit_boxes = []
        self.render_after_id = None
        self.poll_after_id = None
        self.closed = False

        configure_windows_app_identity()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Neurodot | Review image quality")
        self.root.configure(bg=GUI_BG)
        self.root.minsize(960, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.request_close)
        self._set_icon()

        screen_width = max(1024, int(self.root.winfo_screenwidth()))
        # Approximately ten images fit across at the normal zoom level.
        self.base_tile_width = int(np.clip((screen_width - 150) / 10.0, 80, 180))
        self._build()

    def _set_icon(self):
        if Path(GUI_ICON_ICO_PATH).is_file():
            try:
                self.root.iconbitmap(str(GUI_ICON_ICO_PATH))
                self.root.iconbitmap(default=str(GUI_ICON_ICO_PATH))
            except Exception:
                pass
        try:
            if Path(GUI_ICON_PNG_PATH).is_file():
                icon = self.tk.PhotoImage(file=str(GUI_ICON_PNG_PATH))
                self.root.iconphoto(True, icon)
                self._window_icon = icon
        except Exception:
            self._window_icon = None

    def _button(self, parent, text, command, width=10):
        return self.tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=GUI_CONTROL_BG,
            fg=GUI_FG,
            activebackground=GUI_CONTROL_ACTIVE_BG,
            activeforeground=GUI_FG,
            disabledforeground="#6f767a",
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Segoe UI Semibold", 9),
            cursor="hand2",
            padx=9,
            pady=5,
        )

    def _bordered_button(self, parent, text, command, width=10, outline=None):
        """Build a platform-independent outlined button like the main GUI."""
        border = self.tk.Frame(
            parent,
            bg=outline or GUI_BORDER,
            bd=0,
            padx=2,
            pady=2,
        )
        button = self._button(border, text, command, width)
        button.pack(fill="both", expand=True)
        return border, button

    def _build(self):
        top = self.tk.Frame(self.root, bg=GUI_PANEL_BG, padx=14, pady=10)
        top.pack(fill="x")

        title_column = self.tk.Frame(top, bg=GUI_PANEL_BG)
        title_column.pack(side="left", fill="x", expand=True)
        self.tk.Label(
            title_column,
            text="REVIEW IMAGE QUALITY",
            bg=GUI_PANEL_BG,
            fg=GUI_ACCENT,
            font=("Segoe UI Semibold", 12),
        ).pack(anchor="w")
        self.tk.Label(
            title_column,
            text=(
                "All files start included. Left-click a tile to exclude or restore it. "
                "Right-drag to pan; use the mouse wheel to zoom. Other channels "
                "preload in the background."
            ),
            bg=GUI_PANEL_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(2, 0))

        channel_group = self.tk.Frame(top, bg=GUI_PANEL_BG)
        channel_group.pack(side="left", padx=(18, 16))
        self.tk.Label(
            channel_group,
            text="DISPLAY CHANNEL",
            bg=GUI_PANEL_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI Semibold", 8),
        ).pack(side="left", padx=(0, 9))
        self.channel_buttons = {}
        self.channel_button_borders = {}
        for channel in OVERVIEW_CHANNELS:
            border, button = self._bordered_button(
                channel_group,
                channel,
                lambda value=channel: self.set_channel(value),
                width=6,
            )
            border.pack(side="left", padx=(0, 3))
            self.channel_buttons[channel] = button
            self.channel_button_borders[channel] = border

        zoom_group = self.tk.Frame(top, bg=GUI_PANEL_BG)
        zoom_group.pack(side="left", padx=(0, 16))
        self.tk.Label(
            zoom_group,
            text="ZOOM",
            bg=GUI_PANEL_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI Semibold", 8),
        ).pack(side="left", padx=(0, 9))
        zoom_out_border, _zoom_out_button = self._bordered_button(
            zoom_group, "-", lambda: self.change_zoom(1 / OVERVIEW_ZOOM_STEP), 3
        )
        zoom_out_border.pack(side="left", padx=(0, 3))
        reset_border, _reset_button = self._bordered_button(
            zoom_group, "Reset", self.reset_zoom, 7
        )
        reset_border.pack(side="left", padx=(0, 3))
        zoom_in_border, _zoom_in_button = self._bordered_button(
            zoom_group, "+", lambda: self.change_zoom(OVERVIEW_ZOOM_STEP), 3
        )
        zoom_in_border.pack(side="left")

        self.continue_border, self.continue_button = self._bordered_button(
            top,
            "Continue",
            self.accept,
            18,
            outline=GUI_ACCENT,
        )
        self.continue_button.configure(
            bg=GUI_ACCENT,
            fg="#071009",
            activebackground="#68e67c",
            activeforeground="#071009",
            font=("Segoe UI Semibold", 9),
        )
        self.continue_border.pack(side="right")

        status_bar = self.tk.Frame(self.root, bg=GUI_BG, padx=14, pady=7)
        status_bar.pack(fill="x")
        self.status_var = self.tk.StringVar()
        self.tk.Label(
            status_bar,
            textvariable=self.status_var,
            bg=GUI_BG,
            fg=GUI_FG,
            font=("Segoe UI Semibold", 9),
        ).pack(side="left")
        self.tk.Label(
            status_bar,
            text=(
                (
                    "Excluded files are moved only after you confirm Continue."
                )
                if self.apply_exclusions
                else "Overview-only development mode: no files will be moved."
            ),
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI", 8),
        ).pack(side="right")

        canvas_frame = self.tk.Frame(self.root, bg=GUI_BG)
        canvas_frame.pack(fill="both", expand=True)
        self.canvas = self.tk.Canvas(
            canvas_frame,
            bg="#000000",
            highlightthickness=0,
            xscrollincrement=1,
            yscrollincrement=1,
        )
        h_scroll = self.tk.Scrollbar(
            canvas_frame, orient="horizontal", command=self.canvas.xview
        )
        v_scroll = self.tk.Scrollbar(
            canvas_frame, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<ButtonPress-3>", self.on_pan_start)
        self.canvas.bind("<B3-Motion>", self.on_pan_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_pan_end)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)
        self.canvas.bind("<Configure>", lambda _event: self.schedule_render())

        self._update_channel_buttons()
        self._update_status()

    def _update_channel_buttons(self):
        for channel, button in self.channel_buttons.items():
            active = channel == self.current_channel
            self.channel_button_borders[channel].configure(
                bg=GUI_ACCENT if active else GUI_BORDER,
            )
            button.configure(
                fg=GUI_FG if active else GUI_MUTED_FG,
                bg=GUI_CONTROL_BG,
                activebackground=GUI_CONTROL_ACTIVE_BG,
            )

    def _update_status(self):
        selected_count = sum(self.selected.values())
        excluded_count = len(self.ims_files) - selected_count
        loaded_count = sum(
            1
            for path in self.ims_files
            if (path, self.current_channel) in self.preview_cache
        )
        cached_count = len(self.preview_cache)
        cache_target = len(self.ims_files) * len(OVERVIEW_CHANNELS)
        self.status_var.set(
            f"Included: {selected_count} of {len(self.ims_files)}    "
            f"Excluded: {excluded_count}    "
            f"Channel: {self.current_channel}    "
            f"Loaded: {loaded_count} of {len(self.ims_files)}    "
            f"Preloaded: {cached_count} of {cache_target}    "
            f"Zoom: {self.zoom:.2f}x"
        )
        loading = self._channel_is_loading(self.current_channel)
        self.continue_button.configure(
            text=("Loading previews..." if loading else f"Continue with {selected_count}"),
            state="disabled" if loading else "normal",
            cursor="arrow" if loading else "hand2",
        )
        self.continue_border.configure(bg=GUI_BORDER if loading else GUI_ACCENT)

    def _load_preview(self, path, channel):
        mip = read_qc_mip_for_file_channel(
            path,
            channel,
            target_size=OVERVIEW_PREVIEW_MAX_SIZE,
        )
        if mip is None:
            raise RuntimeError(f"Channel {channel} is unavailable")
        white = suggest_setup_preview_white(mip)
        windowed = apply_manual_exposure(mip, SETUP_PREVIEW_BLACK, white)
        u8 = (np.clip(windowed, 0.0, 1.0) * 255.0).astype(np.uint8)
        image = self.Image.fromarray(u8, mode="L")
        image.thumbnail(
            (OVERVIEW_PREVIEW_MAX_SIZE, OVERVIEW_PREVIEW_MAX_SIZE),
            self.Image.Resampling.LANCZOS,
        )
        return image, float(white)

    def _channel_is_loading(self, channel):
        return any(key[1] == channel for key in self.pending)

    def _submit_preview(self, key, *, background):
        if key in self.preview_cache or key in self.pending:
            return

        executor = (
            self.background_executor if background else self.foreground_executor
        )
        self.pending.add(key)
        future = executor.submit(self._load_preview, *key)
        futures = self.background_futures if background else self.foreground_futures
        futures[key] = future

        def finished(item, completed):
            if completed.cancelled():
                return
            try:
                image, white = completed.result()
                payload = (item, image, white, None)
            except BaseException as exc:
                payload = (item, None, None, str(exc))
            self.events.put(payload)

        future.add_done_callback(lambda completed, item=key: finished(item, completed))

    def _demote_hidden_foreground_loads(self):
        """Keep foreground workers focused on the channel the user can see."""
        for key, future in list(self.foreground_futures.items()):
            if key[1] == self.current_channel or not future.cancel():
                continue
            self.foreground_futures.pop(key, None)
            self.pending.discard(key)
            self._submit_preview(key, background=True)

    def _queue_channel_loads(self):
        channel = self.current_channel
        self._demote_hidden_foreground_loads()
        for path in self.ims_files:
            key = (path, channel)
            if key in self.preview_cache:
                continue

            background_future = self.background_futures.get(key)
            if background_future is not None:
                if not background_future.cancel():
                    # It is already running or has just completed; its result
                    # will arrive shortly without duplicating the HDF5 read.
                    continue
                self.background_futures.pop(key, None)
                self.pending.discard(key)

            if key not in self.pending:
                self._submit_preview(key, background=False)
        self._update_status()

    def _queue_background_preloads(self):
        """Load every non-visible channel without delaying visible previews."""
        for channel in OVERVIEW_CHANNELS:
            if channel == self.current_channel:
                continue
            for path in self.ims_files:
                self._submit_preview((path, channel), background=True)
        self._update_status()

    def _poll_events(self):
        if self.closed:
            return
        changed = False
        while True:
            try:
                key, image, white, error = self.events.get_nowait()
            except queue.Empty:
                break
            self.pending.discard(key)
            self.foreground_futures.pop(key, None)
            self.background_futures.pop(key, None)
            self.preview_cache[key] = {
                "image": image,
                "white": white,
                "error": error,
            }
            changed = True
        if changed:
            self.schedule_render()
            self._update_status()
        self.poll_after_id = self.root.after(60, self._poll_events)

    @staticmethod
    def _fit_size(image_size, box_width, box_height):
        width, height = image_size
        scale = min(box_width / max(1, width), box_height / max(1, height))
        return max(1, int(round(width * scale))), max(1, int(round(height * scale)))

    def schedule_render(self):
        if self.closed:
            return
        if self.render_after_id is not None:
            try:
                self.root.after_cancel(self.render_after_id)
            except Exception:
                pass
        self.render_after_id = self.root.after(80, self.render)

    def render(self):
        if self.closed:
            return
        self.render_after_id = None
        self.canvas.delete("all")
        self.photo_images = []
        self.hit_boxes = []

        gap = max(7, int(round(9 * self.zoom)))
        tile_width = max(75, int(round(self.base_tile_width * self.zoom)))
        image_height = max(60, int(round(tile_width * 0.72)))
        label_height = max(24, int(round(30 * min(self.zoom, 2.0))))
        tile_height = image_height + label_height
        viewport_width = max(300, int(self.canvas.winfo_width()))
        columns = max(1, int((viewport_width - gap) / (tile_width + gap)))
        font_size = int(np.clip(8 * math.sqrt(self.zoom), 8, 18))

        for index, path in enumerate(self.ims_files):
            row, column = divmod(index, columns)
            x1 = gap + column * (tile_width + gap)
            y1 = gap + row * (tile_height + gap)
            x2 = x1 + tile_width
            y2 = y1 + tile_height
            image_y2 = y1 + image_height
            included = self.selected[path]
            border_color = (
                OVERVIEW_INCLUDED_BORDER if included else OVERVIEW_EXCLUDED_COLOR
            )
            border_width = (
                max(1, int(round(math.sqrt(self.zoom))))
                if included
                else max(3, int(round(3 * math.sqrt(self.zoom))))
            )

            self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline=border_color,
                width=border_width,
                fill="#080a0c",
            )
            entry = self.preview_cache.get((path, self.current_channel))
            if entry is None:
                self.canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + image_y2) / 2,
                    text="Loading...",
                    fill=GUI_MUTED_FG,
                    font=("Segoe UI", font_size),
                )
            elif entry["error"] is not None:
                self.canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + image_y2) / 2,
                    text=f"Could not load\n{entry['error']}",
                    fill="#ff8888",
                    width=max(50, tile_width - 12),
                    justify="center",
                    font=("Segoe UI", font_size),
                )
            else:
                image = entry["image"]
                fitted = self._fit_size(
                    image.size,
                    max(1, tile_width - 2 * border_width),
                    max(1, image_height - 2 * border_width),
                )
                resized_key = (path, self.current_channel, fitted)
                resized = self.resized_preview_cache.get(resized_key)
                if resized is None:
                    resized = image.resize(fitted, self.Image.Resampling.LANCZOS)
                    self.resized_preview_cache[resized_key] = resized
                photo = self.ImageTk.PhotoImage(resized, master=self.root)
                self.photo_images.append(photo)
                self.canvas.create_image(
                    (x1 + x2) / 2,
                    (y1 + image_y2) / 2,
                    image=photo,
                    anchor="center",
                )
                self.canvas.create_text(
                    x1 + 5,
                    y1 + 5,
                    text=str(index + 1),
                    fill="#ffffff",
                    anchor="nw",
                    font=("Segoe UI Semibold", font_size),
                )

            label_text = path.name if included else f"{path.name}\nEXCLUDED"
            self.canvas.create_text(
                (x1 + x2) / 2,
                image_y2 + 3,
                text=label_text,
                fill=(OVERVIEW_INCLUDED_TEXT if included else border_color),
                width=max(50, tile_width - 8),
                anchor="n",
                justify="center",
                font=("Segoe UI Semibold", font_size),
            )
            self.hit_boxes.append((x1, y1, x2, y2, path))

        rows = max(1, math.ceil(len(self.ims_files) / columns))
        total_width = max(viewport_width, gap + columns * (tile_width + gap))
        total_height = gap + rows * (tile_height + gap)
        self.canvas.configure(scrollregion=(0, 0, total_width, total_height))
        self._update_status()

    def set_channel(self, channel):
        if channel == self.current_channel:
            return
        self.current_channel = channel
        self._update_channel_buttons()
        self._queue_channel_loads()
        self._queue_background_preloads()
        self.schedule_render()
        self._update_status()

    def on_left_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        for x1, y1, x2, y2, path in self.hit_boxes:
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.selected[path] = not self.selected[path]
                self.schedule_render()
                self._update_status()
                return

    def on_pan_start(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.configure(cursor="fleur")

    def on_pan_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_pan_end(self, _event=None):
        self.canvas.configure(cursor="")

    def on_mousewheel(self, event):
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            factor = OVERVIEW_ZOOM_STEP
        elif getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            factor = 1 / OVERVIEW_ZOOM_STEP
        else:
            return "break"
        self.change_zoom(factor, event)
        return "break"

    def change_zoom(self, factor, event=None):
        old_zoom = self.zoom
        new_zoom = float(np.clip(
            old_zoom * factor,
            OVERVIEW_ZOOM_MIN,
            OVERVIEW_ZOOM_MAX,
        ))
        if abs(new_zoom - old_zoom) < 1e-9:
            return

        old_region = self.canvas.bbox("all") or (0, 0, 1, 1)
        old_width = max(1.0, float(old_region[2] - old_region[0]))
        old_height = max(1.0, float(old_region[3] - old_region[1]))
        anchor_x = event.x if event is not None else self.canvas.winfo_width() / 2
        anchor_y = event.y if event is not None else self.canvas.winfo_height() / 2
        fraction_x = self.canvas.canvasx(anchor_x) / old_width
        fraction_y = self.canvas.canvasy(anchor_y) / old_height

        self.zoom = new_zoom
        self.resized_preview_cache.clear()
        self.render()
        self.root.update_idletasks()
        new_region = self.canvas.bbox("all") or (0, 0, 1, 1)
        new_width = max(1.0, float(new_region[2] - new_region[0]))
        new_height = max(1.0, float(new_region[3] - new_region[1]))
        self.canvas.xview_moveto(
            max(0.0, (fraction_x * new_width - anchor_x) / new_width)
        )
        self.canvas.yview_moveto(
            max(0.0, (fraction_y * new_height - anchor_y) / new_height)
        )

    def reset_zoom(self):
        self.zoom = 1.0
        self.resized_preview_cache.clear()
        self.render()
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)

    def accept(self):
        if self._channel_is_loading(self.current_channel):
            self.messagebox.showinfo(
                "Previews are still loading",
                "Please wait until the current preview loading has finished.",
                parent=self.root,
            )
            return

        included = [path for path in self.ims_files if self.selected[path]]
        excluded = [path for path in self.ims_files if not self.selected[path]]
        if not included:
            self.messagebox.showwarning(
                "No files selected",
                "Keep at least one IMS file selected before continuing.",
                parent=self.root,
            )
            return

        if excluded and self.apply_exclusions:
            destination = self.input_dir / EXCLUDED_FOLDER_NAME
            approved = self.messagebox.askyesno(
                "Move excluded files?",
                f"Move {len(excluded)} excluded IMS file(s) to:\n\n"
                f"{destination}\n\n"
                "They will not be counted. Move them back into the input folder "
                "to restore them.",
                parent=self.root,
                icon="question",
            )
            if not approved:
                return

        self.result = {"included": included, "excluded": excluded}
        self._close()

    def request_close(self):
        if self.messagebox.askyesno(
            "Close Neurodot?",
            "Close without moving or processing any files?",
            parent=self.root,
            icon="question",
        ):
            self.result = None
            self._close()

    def _close(self):
        self.closed = True
        for after_id in (self.poll_after_id, self.render_after_id):
            if after_id is not None:
                try:
                    self.root.after_cancel(after_id)
                except Exception:
                    pass
        self.foreground_executor.shutdown(wait=True, cancel_futures=True)
        self.background_executor.shutdown(wait=True, cancel_futures=True)
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.update_idletasks()
        self.root.deiconify()
        try:
            self.root.state("zoomed")
        except Exception:
            try:
                self.root.attributes("-zoomed", True)
            except Exception:
                pass
        self.root.lift()
        self.root.focus_force()
        self._queue_channel_loads()
        self._queue_background_preloads()
        self.poll_after_id = self.root.after(60, self._poll_events)
        self.schedule_render()
        self.root.mainloop()
        return self.result


def unique_excluded_path(folder, filename):
    """Return a collision-free destination without overwriting prior files."""
    candidate = folder / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 2
    while True:
        candidate = folder / f"{stem}__{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def move_excluded_files(excluded_files, input_dir):
    """Move exclusions recoverably and roll back if any individual move fails."""
    excluded_files = [Path(path) for path in excluded_files]
    if not excluded_files:
        return []

    destination_dir = Path(input_dir) / EXCLUDED_FOLDER_NAME
    destination_dir.mkdir(parents=True, exist_ok=True)
    moved = []
    try:
        for source in excluded_files:
            destination = unique_excluded_path(destination_dir, source.name)
            shutil.move(str(source), str(destination))
            moved.append((source, destination))
    except Exception:
        for source, destination in reversed(moved):
            if destination.exists() and not source.exists():
                shutil.move(str(destination), str(source))
        raise

    manifest_path = destination_dir / "exclusion_manifest.json"
    try:
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, list):
                manifest = []
        else:
            manifest = []
        timestamp = datetime.now().isoformat(timespec="seconds")
        manifest.extend(
            {
                "excluded_at": timestamp,
                "original_path": str(source),
                "moved_to": str(destination),
            }
            for source, destination in moved
        )
        temporary = manifest_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        temporary.replace(manifest_path)
    except Exception:
        # A manifest is helpful but is not the authoritative file operation.
        pass

    return [destination for _source, destination in moved]


def choose_image_quality_overview(ims_files, input_dir, progress=None):
    """Review the series, apply confirmed exclusions, and return included files."""
    if progress is not None:
        progress.update(
            "Opening the image-quality overview...",
            "Preparing high-resolution g-channel MIPs for the complete series.",
        )
        progress.close()

    review = ImageQualityOverviewWindow(ims_files, input_dir=input_dir).run()
    if review is None:
        return None

    move_excluded_files(review["excluded"], input_dir)
    return list(review["included"])


def preview_selection_only(ims_files):
    """Open the overview without moving files, for isolated UI development."""
    return ImageQualityOverviewWindow(
        ims_files,
        input_dir=Path(IMS_INPUT_DIR),
        apply_exclusions=False,
    ).run()
