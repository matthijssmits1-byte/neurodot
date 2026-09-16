"""Tkinter exposure, landmark, channel, and custom-ROI interface."""
from .common import *
from .config import *
from .image_io import *
from .detection import *
from .geometry import *
class ExposureWindowGUI:
    """
    Series exposure + per-image landmark editor.

    Exposure behavior
    -----------------
    Each image/channel can be explicitly assigned its own black/white window.

    If an image/channel is left UNSET:
        it receives the arithmetic mean black/white values of all explicitly
        set images for that channel in this series.

    If no image has been explicitly set for a channel:
        the initial channel baseline (previous saved value when available,
        otherwise the automatically suggested value) is used.

    Landmark behavior
    -----------------
    Each image starts with a bottom-midline click and a drag-to-place top
    midline point. The centre is placed automatically at their exact midpoint,
    after which si/bo/to are placed for L and R. All dots are displayed on
    every channel preview for that image, and ce remains manually editable.
    """
    def __init__(
        self,
        ims_files,
        loaded_models,
        loading_callback=None,
    ):
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog
        from PIL import Image, ImageTk, ImageDraw, ImageFont

        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox
        self.filedialog = filedialog
        self.Image = Image
        self.ImageTk = ImageTk
        self.ImageDraw = ImageDraw
        self.ImageFont = ImageFont

        self.ims_files = list(
            ims_files
        )
        self.loaded_models = loaded_models
        self.loading_callback = loading_callback
        self.previous = (
            _load_previous_exposure_settings()
        )

        configure_windows_app_identity()
        self.root = tk.Tk()
        # Build the themed interface while hidden. Otherwise Windows can paint
        # Tk's default white client area for a frame before the dark styles and
        # image canvas are ready.
        self.root.withdraw()
        self.root.title(
            "Neurodot | Advanced cell detection"
        )
        self._configure_dark_theme()
        self._load_gui_graphics()
        self.placement_cursor = self._create_native_placement_cursor()

        screen_w = int(
            self.root.winfo_screenwidth()
        )
        screen_h = int(
            self.root.winfo_screenheight()
        )

        window_w = min(
            1760,
            max(
                1150,
                screen_w - 30,
            ),
        )

        window_h = min(
            1060,
            max(
                760,
                screen_h - 50,
            ),
        )

        self.root.geometry(
            f"{window_w}x{window_h}"
        )

        self.root.minsize(
            1050,
            720,
        )
        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.request_close,
        )

        self._initial_loading_frame = None
        if self.loading_callback is None:
            self._show_initial_loading()
            self.loading_callback = self._update_initial_loading

        self.accepted = False
        self.result = None

        self.current_file_index = 0
        self.current_channel = (
            CHANNEL_PROCESSING_ORDER[
                0
            ]
        )

        self.current_landmark = first_manual_landmark_key()

        # Current explicit image/channel overrides:
        #   (file_index, channel) -> {black, white}
        # Missing key means "use series average".
        self.image_exposure_overrides = {}

        # Per-image logical-pixel coordinates:
        #   file_index -> {"ce": [y,x], "si": ..., ...}
        self.manual_landmarks_yx = {
            i: {}
            for i in range(
                len(
                    self.ims_files
                )
            )
        }

        # Baseline per channel used until at least one image is explicitly set.
        self.channel_baseline = {}

        # This workstation has ample RAM, so keep a generous full-resolution MIP
        # cache. Expensive HDF5/MIP work is performed in background workers so
        # Tkinter itself never blocks on a multi-hundred-MB channel read.
        self.mip_cache = {}
        self.mip_cache_order = []

        requested_cache_items = int(GUI_MIP_CACHE_ITEMS)
        if GUI_PRELOAD_ALL_MIPS:
            requested_cache_items = max(
                requested_cache_items,
                len(self.ims_files) * len(CHANNEL_PROCESSING_ORDER),
            )
        self.max_cache_items = requested_cache_items

        self.mip_executor = ThreadPoolExecutor(
            max_workers=max(1, int(GUI_MIP_WORKERS)),
            thread_name_prefix="imaris_mip",
        )
        self.mip_futures = {}

        # Keep Cellpose test inference off Tkinter's event thread. A single
        # worker is intentional so the shared GPU model is never evaluated by
        # two GUI test jobs at once.
        self.cellpose_test_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="cellpose_gui_test",
        )
        self.cellpose_test_future = None
        self.cellpose_test_started_at = None
        self.cellpose_test_context = None
        self._cellpose_test_poll_after_id = None

        # Original widget cursors are saved while a Cellpose test is running so
        # the Windows wait/hourglass cursor can be shown consistently across
        # the entire GUI, including buttons, sliders and the preview canvas.
        self._busy_cursor_restore = {}

        self.preview_after_id = None
        self._mip_poll_after_id = None

        self.photo = None
        self.preview_scale = 1.0
        self.preview_offset_x = 0.0
        self.preview_offset_y = 0.0
        self.preview_display_size = (
            1,
            1,
        )
        self.preview_native_shape = (
            1,
            1,
        )

        self.preview_zoom = 1.0
        self.preview_pan_x = 0.0
        self.preview_pan_y = 0.0
        self.preview_fit_scale = 1.0
        self.preview_pan_active = False
        self.preview_pan_last_xy = None

        # Fully composited native-resolution preview kept in RAM. Zooming only
        # resizes this cached image instead of recalculating exposure and all
        # overlays on every wheel event.
        self.preview_native_pil = None
        self.preview_image_item = None

        # Persistent Cellpose test overlays, keyed by (file_index, channel).
        self.cellpose_preview_results = {}
        self.show_cellpose_preview_var = tk.BooleanVar(value=True)

        # One series-wide anatomical selection is stored independently for
        # each fluorescence channel. The radio buttons display/edit the
        # selection belonging to the currently viewed channel.
        self.channel_counting_regions = {
            channel: DEFAULT_COUNTING_REGION
            for channel in CHANNEL_PROCESSING_ORDER
        }
        self.counting_region_var = tk.StringVar(
            value=self.channel_counting_regions[self.current_channel]
        )

        # Optional freehand counting polygons, independently stored for every
        # image/channel/hemisphere in logical native-image (y, x) coordinates.
        self.custom_counting_rois_yx = {}
        self.custom_counting_roi_modes = {}
        self.custom_roi_hemisphere_var = tk.StringVar(value="L")
        self.custom_roi_exclusion_var = tk.BooleanVar(value=False)
        self.custom_roi_draw_active = False
        self.custom_roi_draft_yx = []
        self.custom_roi_canvas_tag = "custom_counting_roi_draft"

        # Per-image/channel exposure calibration selections.
        self.exposure_pick_mode = None
        self.exposure_calibration_picks = {}
        # Completed exposure selections must display their effective values
        # rather than silently returning to the temporary black=0 preview.
        self.exposure_finalized_keys = set()

        # Automatic landmark advancement is used only for the initial pass.
        # Later point corrections are explicit one-shot replacements.
        self.landmark_sequence_active = True

        # Lightweight interactive midline drag state.  The top midline point
        # is committed only when the mouse button is released; while dragging,
        # only a Canvas overlay is updated (the microscopy preview is not
        # rerendered on every mouse-motion event).
        self.midline_drag_active = False
        self.midline_drag_tag = "midline_drag_preview"

        self.loading_sliders = False

        self._build_widgets()
        self._initialize_channel_baselines()
        self._load_effective_exposure_into_sliders()
        self._schedule_mip_poll()

        if GUI_PRELOAD_ALL_MIPS:
            self._prefetch_all_mips()
        else:
            self._prefetch_nearby_mips()

        self.refresh_preview()
        self._hide_initial_loading()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _show_initial_loading(self):
        """Show a dark loading surface using this GUI's own Tcl interpreter."""
        tk = self.tk
        frame = tk.Frame(self.root, bg=GUI_BG)
        frame.place(x=0, y=0, relwidth=1, relheight=1)

        content = tk.Frame(frame, bg=GUI_BG)
        content.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(
            content,
            text="LOADING IMAGE SERIES",
            bg=GUI_BG,
            fg=GUI_ACCENT,
            font=("Segoe UI Semibold", 14),
        ).pack()
        self._initial_loading_status = tk.StringVar(value="Opening IMS files...")
        self._initial_loading_detail = tk.StringVar(
            value="Preparing the initial channel previews."
        )
        tk.Label(
            content,
            textvariable=self._initial_loading_status,
            bg=GUI_BG,
            fg=GUI_FG,
            font=("Segoe UI Semibold", 10),
        ).pack(pady=(18, 4))
        tk.Label(
            content,
            textvariable=self._initial_loading_detail,
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI", 9),
        ).pack()
        self._initial_loading_progress = self.ttk.Progressbar(
            content,
            mode="determinate",
            maximum=max(1, len(CHANNEL_PROCESSING_ORDER)),
            length=380,
        )
        self._initial_loading_progress.pack(pady=(16, 0))
        self._initial_loading_frame = frame
        self.root.deiconify()
        frame.lift()
        self.root.update_idletasks()
        self.root.update()

    def _update_initial_loading(self, status, detail="", current=None, total=None):
        if self._initial_loading_frame is None:
            return
        self._initial_loading_status.set(str(status))
        self._initial_loading_detail.set(str(detail))
        if total:
            self._initial_loading_progress.configure(maximum=max(1, int(total)))
        if current is not None:
            self._initial_loading_progress["value"] = int(current)
        self._initial_loading_frame.lift()
        self.root.update_idletasks()
        self.root.update()

    def _hide_initial_loading(self):
        if self._initial_loading_frame is None:
            return
        self._initial_loading_frame.destroy()
        self._initial_loading_frame = None
        self.root.withdraw()

    def _configure_dark_theme(self):
        """Apply a black/dark theme to the Tk/ttk interface only."""
        tk = self.tk
        ttk = self.ttk

        self.root.configure(background=GUI_BG)

        style = ttk.Style(self.root)
        # The clam engine respects custom colours much more consistently than
        # the native Windows ttk theme.
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=GUI_BG)
        style.configure("Header.TFrame", background=GUI_PANEL_BG)
        style.configure(
            "ControlGroup.TFrame",
            background=GUI_PANEL_BG,
            bordercolor=GUI_BORDER,
            relief="flat",
        )
        style.configure(
            "TLabel",
            background=GUI_BG,
            foreground=GUI_FG,
        )
        style.configure(
            "Header.TLabel",
            background=GUI_PANEL_BG,
            foreground=GUI_FG,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Section.TLabel",
            background=GUI_PANEL_BG,
            foreground=GUI_MUTED_FG,
            font=("Segoe UI Semibold", 8),
        )
        style.configure(
            "File.TLabel",
            background=GUI_PANEL_BG,
            foreground=GUI_FG,
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "Status.TLabel",
            background=GUI_PANEL_BG,
            foreground=GUI_MUTED_FG,
            font=("Segoe UI", 8),
        )
        style.configure(
            "TButton",
            background=GUI_CONTROL_BG,
            foreground=GUI_FG,
            bordercolor=GUI_BORDER,
            lightcolor=GUI_CONTROL_BG,
            darkcolor=GUI_CONTROL_BG,
            padding=(7, 4),
        )
        style.map(
            "TButton",
            background=[
                ("active", GUI_CONTROL_ACTIVE_BG),
                ("pressed", GUI_CONTROL_ACTIVE_BG),
            ],
            foreground=[
                ("disabled", "#6f767a"),
                ("!disabled", GUI_FG),
            ],
        )
        style.configure(
            "Header.TButton",
            background=GUI_CONTROL_BG,
            foreground=GUI_FG,
            bordercolor=GUI_BORDER,
            padding=(9, 5),
            font=("Segoe UI", 9),
        )
        style.configure(
            "Primary.TButton",
            background=GUI_ACCENT,
            foreground="#071009",
            bordercolor=GUI_ACCENT,
            lightcolor=GUI_ACCENT,
            darkcolor=GUI_ACCENT,
            padding=(15, 6),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", "#68e67c"),
                ("pressed", "#43c75a"),
            ],
            foreground=[("!disabled", "#071009")],
        )
        style.configure(
            "Header.TCheckbutton",
            background=GUI_PANEL_BG,
            foreground=GUI_FG,
            indicatorcolor=GUI_CONTROL_BG,
            padding=(3, 2),
            font=("Segoe UI", 9),
        )
        style.map(
            "Header.TCheckbutton",
            background=[("active", GUI_PANEL_BG)],
            indicatorcolor=[
                ("selected", GUI_ACCENT),
                ("!selected", GUI_CONTROL_BG),
            ],
        )
        style.configure(
            "TRadiobutton",
            background=GUI_BG,
            foreground=GUI_FG,
            indicatorcolor=GUI_CONTROL_BG,
        )
        style.map(
            "TRadiobutton",
            background=[("active", GUI_BG)],
            foreground=[("active", GUI_FG)],
            indicatorcolor=[
                ("selected", GUI_ACCENT),
                ("!selected", GUI_CONTROL_BG),
            ],
        )
        style.configure(
            "TSeparator",
            background=GUI_BORDER,
        )
        style.configure(
            "Channel.TButton",
            background=GUI_CONTROL_BG,
            foreground=GUI_FG,
            bordercolor=GUI_BORDER,
            lightcolor=GUI_CONTROL_BG,
            darkcolor=GUI_CONTROL_BG,
            borderwidth=1,
            padding=(14, 5),
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "ActiveChannel.TButton",
            background=GUI_CONTROL_BG,
            foreground=GUI_FG,
            bordercolor=GUI_ACCENT,
            lightcolor=GUI_ACCENT,
            darkcolor=GUI_ACCENT,
            borderwidth=2,
            padding=(13, 4),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "ActiveChannel.TButton",
            background=[
                ("active", GUI_CONTROL_ACTIVE_BG),
                ("pressed", GUI_CONTROL_ACTIVE_BG),
            ],
            bordercolor=[
                ("!disabled", GUI_ACCENT),
            ],
        )

    def _load_gui_graphics(self):
        """Load optional Neurodot icon and looping footer video."""
        self.window_icon_photo = None
        self.banner_photo = None
        self.banner_source_image = None
        self.banner_label = None
        self.right_panel = None

        self.logo_video_capture = None
        self.logo_video_after_id = None
        self.logo_video_delay_ms = int(round(1000.0 / GUI_VIDEO_FPS_FALLBACK))
        self.cv2 = None

        # On Windows, iconphoto alone can leave a Tk window represented by the
        # generic Python/Tk icon in the taskbar. Use the multi-resolution ICO
        # as the native window icon and retain iconphoto for other platforms.
        if GUI_ICON_ICO_PATH.is_file():
            try:
                self.root.iconbitmap(str(GUI_ICON_ICO_PATH))
                self.root.iconbitmap(default=str(GUI_ICON_ICO_PATH))
            except Exception as exc:
                print(
                    f"GUI taskbar icon could not be loaded from "
                    f"{GUI_ICON_ICO_PATH}: {exc}"
                )

        if GUI_ICON_PATH.is_file():
            try:
                # Use Tk's native PNG loader, matching the startup window that
                # Windows already represents correctly in the taskbar.
                self.window_icon_photo = self.tk.PhotoImage(
                    master=self.root,
                    file=str(GUI_ICON_PATH),
                )
                self.root.iconphoto(False, self.window_icon_photo)
                self.root.iconphoto(True, self.window_icon_photo)
                self.root.after_idle(
                    lambda: self.root.iconphoto(False, self.window_icon_photo)
                )
            except Exception as exc:
                print(
                    f"GUI icon could not be loaded from {GUI_ICON_PATH}: {exc}"
                )

        # Prefer the rotating MP4. OpenCV is used only for lightweight GUI
        # playback; Cellpose/image processing is otherwise unchanged.
        if GUI_SHOW_BANNER and GUI_VIDEO_PATH.is_file():
            try:
                import cv2

                capture = cv2.VideoCapture(str(GUI_VIDEO_PATH))
                if not capture.isOpened():
                    raise RuntimeError("OpenCV could not open the MP4.")

                fps = float(capture.get(cv2.CAP_PROP_FPS))
                if not math.isfinite(fps) or fps <= 1.0:
                    fps = float(GUI_VIDEO_FPS_FALLBACK)

                self.cv2 = cv2
                self.logo_video_capture = capture
                self.logo_video_delay_ms = max(
                    15,
                    int(round(1000.0 / fps)),
                )

                print(
                    f"GUI rotating logo: {GUI_VIDEO_PATH.resolve()} "
                    f"({fps:.1f} fps)"
                )
            except Exception as exc:
                print(
                    f"GUI rotating logo could not be loaded from "
                    f"{GUI_VIDEO_PATH}: {exc}"
                )
                print(
                    "  Falling back to the static Neurodot graphic. "
                    "Install opencv-python if MP4 playback support is missing."
                )
                self.logo_video_capture = None
                self.cv2 = None

        # Static fallback.
        if (
            GUI_SHOW_BANNER
            and self.logo_video_capture is None
            and GUI_BANNER_PATH.is_file()
        ):
            try:
                self.banner_source_image = (
                    self.Image.open(GUI_BANNER_PATH).convert("RGBA")
                )
            except Exception as exc:
                print(
                    f"GUI banner could not be loaded from "
                    f"{GUI_BANNER_PATH}: {exc}"
                )
                self.banner_source_image = None


    def _logo_available_width(self):
        available_width = int(GUI_BANNER_MAX_WIDTH)

        if self.right_panel is not None:
            try:
                panel_width = int(self.right_panel.winfo_width())
                if panel_width > 32:
                    available_width = min(
                        int(GUI_BANNER_MAX_WIDTH),
                        max(180, panel_width - 24),
                    )
            except Exception:
                pass

        return available_width


    def _refresh_banner_image(self):
        """Refresh the static fallback image when no MP4 is active."""
        if (
            self.logo_video_capture is not None
            or self.banner_source_image is None
            or self.banner_label is None
        ):
            return

        banner = self.banner_source_image.copy()
        banner.thumbnail(
            (
                int(self._logo_available_width()),
                int(GUI_BANNER_MAX_HEIGHT),
            ),
            getattr(
                getattr(self.Image, "Resampling", self.Image),
                "LANCZOS",
            ),
        )
        self.banner_photo = self.ImageTk.PhotoImage(banner, master=self.root)
        self.banner_label.configure(image=self.banner_photo)


    def _advance_logo_video(self):
        """Display one frame and schedule the next, looping at EOF."""
        self.logo_video_after_id = None

        if (
            self.logo_video_capture is None
            or self.banner_label is None
            or self.cv2 is None
        ):
            return

        try:
            ok, frame = self.logo_video_capture.read()

            if not ok:
                self.logo_video_capture.set(
                    self.cv2.CAP_PROP_POS_FRAMES,
                    0,
                )
                ok, frame = self.logo_video_capture.read()

            if ok:
                frame = self.cv2.cvtColor(
                    frame,
                    self.cv2.COLOR_BGR2RGB,
                )
                pil = self.Image.fromarray(frame)
                pil.thumbnail(
                    (
                        int(self._logo_available_width()),
                        int(GUI_BANNER_MAX_HEIGHT),
                    ),
                    getattr(
                        getattr(self.Image, "Resampling", self.Image),
                        "LANCZOS",
                    ),
                )
                self.banner_photo = self.ImageTk.PhotoImage(pil, master=self.root)
                self.banner_label.configure(image=self.banner_photo)

            if self.root.winfo_exists():
                self.logo_video_after_id = self.root.after(
                    int(self.logo_video_delay_ms),
                    self._advance_logo_video,
                )
        except Exception as exc:
            print(f"GUI rotating logo playback stopped: {exc}")
            self._stop_logo_video()


    def _start_logo_video(self):
        if (
            self.logo_video_capture is not None
            and self.logo_video_after_id is None
        ):
            self._advance_logo_video()


    def _stop_logo_video(self):
        if self.logo_video_after_id is not None:
            try:
                self.root.after_cancel(
                    self.logo_video_after_id
                )
            except Exception:
                pass
            self.logo_video_after_id = None

        if self.logo_video_capture is not None:
            try:
                self.logo_video_capture.release()
            except Exception:
                pass
            self.logo_video_capture = None


    def _on_right_panel_configure(self, _event=None):
        if self.logo_video_capture is None:
            self._refresh_banner_image()


    def _build_widgets(self):
        """Build the compact Neurodot workstation-style GUI."""
        tk = self.tk
        ttk = self.ttk

        # ==============================================================
        # HEADER: navigation/actions above clearly grouped channel controls
        # ==============================================================
        header = ttk.Frame(
            self.root,
            style="Header.TFrame",
            padding=(12, 8, 12, 9),
        )
        header.pack(fill="x")

        topbar = ttk.Frame(header, style="Header.TFrame")
        topbar.pack(fill="x")

        self.file_label = ttk.Label(topbar, text="", style="File.TLabel")
        self.file_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ttk.Button(
            topbar,
            text="◀",
            width=3,
            style="Header.TButton",
            command=self.previous_file,
        ).pack(
            side="left", padx=(0, 1)
        )
        ttk.Button(
            topbar,
            text="▶",
            width=3,
            style="Header.TButton",
            command=self.next_file,
        ).pack(
            side="left", padx=(1, 8)
        )

        # Re-pack after navigation so the filename occupies the remaining
        # centre space between navigation and the right-side actions.
        self.file_label.pack_forget()
        self.file_label.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(4, 12),
        )

        controls_row = ttk.Frame(header, style="Header.TFrame")
        controls_row.pack(fill="x", pady=(8, 0))

        channel_group = ttk.Frame(
            controls_row,
            style="ControlGroup.TFrame",
        )
        channel_group.pack(side="left", padx=(0, 18))
        ttk.Label(
            channel_group,
            text="DISPLAY",
            style="Section.TLabel",
        ).pack(side="left", padx=(0, 7))

        self.channel_buttons = {}
        for channel in CHANNEL_PROCESSING_ORDER:
            button = ttk.Button(
                channel_group,
                text=channel,
                style="Channel.TButton",
                width=6,
                command=lambda ch=channel: self.set_channel(ch),
            )
            button.pack(side="left", padx=(0, 2))
            self.channel_buttons[channel] = button

        self._update_channel_button_styles()

        # Series-wide production-count selection. These checkboxes do not hide
        # channels from the preview; they only control whether production
        # Cellpose inference is run for that logical channel. Disabled channels
        # remain present in the exported Imaris schema and receive the standard
        # single placeholder Spot in each hemisphere output.
        count_group = ttk.Frame(
            controls_row,
            style="ControlGroup.TFrame",
        )
        count_group.pack(side="left", padx=(0, 18))
        ttk.Label(
            count_group,
            text="COUNT",
            style="Section.TLabel",
        ).pack(side="left", padx=(0, 7))

        self.channel_enabled_vars = {}
        self.channel_count_buttons = {}
        self.channel_count_borders = {}
        for channel in CHANNEL_PROCESSING_ORDER:
            var = tk.BooleanVar(value=True)
            self.channel_enabled_vars[channel] = var
            border = tk.Frame(
                count_group,
                background=GUI_BORDER,
                borderwidth=0,
                padx=2,
                pady=2,
            )
            border.pack(
                side="left",
                padx=(0, 2),
            )
            button = tk.Checkbutton(
                border,
                text=channel,
                variable=var,
                command=self._on_channel_count_changed,
                indicatoron=False,
                width=4,
                padx=6,
                pady=5,
                borderwidth=0,
                relief="flat",
                background=GUI_CONTROL_BG,
                foreground=GUI_FG,
                activebackground=GUI_CONTROL_ACTIVE_BG,
                activeforeground=GUI_FG,
                selectcolor=GUI_CONTROL_BG,
                highlightthickness=0,
                font=("Segoe UI Semibold", 9),
            )
            button.pack(
                fill="both",
                expand=True,
            )
            self.channel_count_buttons[channel] = button
            self.channel_count_borders[channel] = border

        self._update_channel_count_button_styles()

        region_group = ttk.Frame(
            controls_row,
            style="ControlGroup.TFrame",
        )
        region_group.pack(side="left")

        self.counting_region_label = ttk.Label(
            region_group,
            text="COUNT AREA",
            style="Section.TLabel",
        )
        self.counting_region_label.pack(side="left", padx=(0, 7))

        self.counting_region_buttons = {}
        self.counting_region_borders = {}
        for value, label in (
            ("whole", "Whole"),
            ("dorsal", "Dorsal"),
            ("ventral", "Ventral"),
        ):
            border = tk.Frame(
                region_group,
                background=GUI_BORDER,
                borderwidth=0,
                padx=2,
                pady=2,
            )
            border.pack(side="left", padx=(0, 2))
            button = tk.Radiobutton(
                border,
                text=label,
                value=value,
                variable=self.counting_region_var,
                command=self._on_counting_region_changed,
                indicatoron=False,
                width=8,
                padx=5,
                pady=4,
                borderwidth=0,
                relief="flat",
                background=GUI_CONTROL_BG,
                foreground=GUI_FG,
                activebackground=GUI_CONTROL_ACTIVE_BG,
                activeforeground=GUI_FG,
                selectcolor=GUI_CONTROL_BG,
                highlightthickness=0,
                font=("Segoe UI", 9),
            )
            button.pack(fill="both", expand=True)
            self.counting_region_buttons[value] = button
            self.counting_region_borders[value] = border

        self._update_counting_region_button_styles()

        self.image_completion_label = ttk.Label(
            controls_row,
            text="",
            style="Status.TLabel",
        )
        self.image_completion_label.pack(side="right", padx=(12, 2))

        ttk.Button(
            topbar,
            text="Save & Continue",
            command=self.accept,
            style="Primary.TButton",
        ).pack(side="right", padx=(7, 0))

        ttk.Button(
            topbar,
            text="Cancel",
            command=self.request_close,
            style="Header.TButton",
        ).pack(
            side="right",
            padx=(4, 0),
        )
        ttk.Button(
            topbar,
            text="Load settings JSON...",
            command=self.load_window_settings_json,
            style="Header.TButton",
        ).pack(side="right", padx=(4, 0))
        ttk.Button(
            topbar,
            text="Save settings JSON...",
            command=self.save_window_settings_json,
            style="Header.TButton",
        ).pack(side="right", padx=(10, 0))

        ttk.Separator(self.root, orient="horizontal").pack(fill="x")

        # ==============================================================
        # FULL-WIDTH EXPOSURE WORKBENCH
        # ==============================================================
        exposure = ttk.Frame(self.root, padding=(12, 7, 12, 6))
        exposure.pack(fill="x")
        exposure.grid_columnconfigure(1, weight=1)

        self.exposure_mode_label = ttk.Label(
            exposure,
            text="",
            foreground=GUI_MUTED_FG,
        )
        self.exposure_mode_label.grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 1)
        )

        self.numeric_label = ttk.Label(exposure, text="", anchor="e")
        self.numeric_label.grid(
            row=0, column=2, columnspan=3, sticky="e", pady=(0, 1)
        )

        self.black_var = tk.DoubleVar(value=0.0)
        self.white_var = tk.DoubleVar(value=1.0)

        ttk.Label(exposure, text="Black", width=7).grid(
            row=1, column=0, sticky="w"
        )

        self.black_scale = tk.Scale(
            exposure,
            variable=self.black_var,
            orient="horizontal",
            resolution=GUI_EXPOSURE_FINE_RESOLUTION,
            length=1400,
            showvalue=True,
            command=self.on_slider,
            background=GUI_BG,
            foreground=GUI_FG,
            activebackground=GUI_ACCENT,
            troughcolor=GUI_CONTROL_BG,
            highlightthickness=0,
            borderwidth=0,
            sliderlength=16,
        )
        self.black_scale.grid(
            row=1, column=1, sticky="ew", padx=(0, 2)
        )

        # +/- are deliberately packed tightly as a visual pair.
        black_nudges = ttk.Frame(exposure)
        black_nudges.grid(row=1, column=2, columnspan=2, sticky="e")
        ttk.Button(
            black_nudges,
            text="−",
            width=3,
            command=lambda: self._nudge_exposure(
                "black", -GUI_EXPOSURE_BUTTON_STEP
            ),
        ).pack(side="left", padx=(0, 0))
        ttk.Button(
            black_nudges,
            text="+",
            width=3,
            command=lambda: self._nudge_exposure(
                "black", GUI_EXPOSURE_BUTTON_STEP
            ),
        ).pack(side="left", padx=(0, 0))

        ttk.Label(exposure, text="White", width=7).grid(
            row=2, column=0, sticky="w"
        )

        self.white_scale = tk.Scale(
            exposure,
            variable=self.white_var,
            orient="horizontal",
            resolution=GUI_EXPOSURE_FINE_RESOLUTION,
            length=1400,
            showvalue=True,
            command=self.on_slider,
            background=GUI_BG,
            foreground=GUI_FG,
            activebackground=GUI_ACCENT,
            troughcolor=GUI_CONTROL_BG,
            highlightthickness=0,
            borderwidth=0,
            sliderlength=16,
        )
        self.white_scale.grid(
            row=2, column=1, sticky="ew", padx=(0, 2)
        )

        white_nudges = ttk.Frame(exposure)
        white_nudges.grid(row=2, column=2, columnspan=2, sticky="e")
        ttk.Button(
            white_nudges,
            text="−",
            width=3,
            command=lambda: self._nudge_exposure(
                "white", -GUI_EXPOSURE_BUTTON_STEP
            ),
        ).pack(side="left", padx=(0, 0))
        ttk.Button(
            white_nudges,
            text="+",
            width=3,
            command=lambda: self._nudge_exposure(
                "white", GUI_EXPOSURE_BUTTON_STEP
            ),
        ).pack(side="left", padx=(0, 0))

        # ==============================================================
        # CALIBRATION STRIP
        # ==============================================================
        calibration = ttk.Frame(exposure)
        calibration.grid(
            row=3, column=0, columnspan=5, sticky="ew", pady=(1, 0)
        )

        ttk.Label(
            calibration,
            text="Calibration:",
            foreground=GUI_MUTED_FG,
        ).pack(side="left", padx=(0, 4))

        self.pick_positive_button = ttk.Button(
            calibration,
            text="1  Weakest positive",
            style="Channel.TButton",
            command=lambda: self._set_exposure_pick_mode("positive"),
        )
        self.pick_positive_button.pack(side="left", padx=1)

        self.pick_background_button = ttk.Button(
            calibration,
            text="2  Brightest background",
            style="Channel.TButton",
            command=lambda: self._set_exposure_pick_mode("background"),
        )
        self.pick_background_button.pack(side="left", padx=1)

        ttk.Button(
            calibration,
            text="Clear picks",
            command=self.clear_exposure_calibration_picks,
        ).pack(side="left", padx=(2, 5))

        self.exposure_pick_status_label = ttk.Label(
            calibration,
            text=(
                f"Weakest positive → brightest background "
                f"({EXPOSURE_PICK_RADIUS_PX}px radius)"
            ),
            foreground=GUI_MUTED_FG,
        )
        self.exposure_pick_status_label.pack(
            side="left", fill="x", expand=True, padx=(5, 3)
        )

        ttk.Button(
            calibration,
            text="Series average",
            command=self.unset_current_image_exposure,
        ).pack(side="right", padx=(1, 0))
        ttk.Button(
            calibration,
            text="Reset exposure",
            command=self.reset_current_exposure,
        ).pack(side="right", padx=(0, 1))

        # ==============================================================
        # BODY: landmarks | preview | Cellpose/tools
        # ==============================================================
        body = ttk.Frame(self.root, padding=(5, 1, 5, 3))
        body.pack(fill="both", expand=True)

        # LEFT RAIL: anatomical landmarks
        landmark_panel = ttk.Frame(body, width=185)
        landmark_panel.pack(side="left", fill="y", padx=(0, 5))
        landmark_panel.pack_propagate(False)

        ttk.Label(
            landmark_panel,
            text="LANDMARKS",
            font=("TkDefaultFont", 9, "bold"),
            foreground=GUI_MUTED_FG,
        ).pack(anchor="w", pady=(1, 2))

        self.landmark_var = tk.StringVar(value=first_manual_landmark_key())
        self.landmark_buttons = {}
        self.landmark_borders = {}

        for key, cfg in MANUAL_GUI_LANDMARKS.items():
            border = tk.Frame(
                landmark_panel,
                background=GUI_BORDER,
                borderwidth=0,
                padx=2,
                pady=2,
            )
            border.pack(fill="x", pady=(0, 2))
            button = tk.Button(
                border,
                text=cfg["label"],
                command=lambda landmark=key: self._select_landmark(landmark),
                anchor="w",
                padx=7,
                pady=3,
                borderwidth=0,
                relief="flat",
                background=GUI_CONTROL_BG,
                foreground=cfg["color"],
                activebackground=GUI_CONTROL_ACTIVE_BG,
                activeforeground=cfg["color"],
                highlightthickness=0,
                font=("Segoe UI", 9),
            )
            button.pack(fill="both", expand=True)
            self.landmark_buttons[key] = button
            self.landmark_borders[key] = border

        self._update_landmark_button_styles()

        self.rotation_label = ttk.Label(
            landmark_panel,
            text="Rotation CCW-only to straight: NOT SET",
            font=("TkDefaultFont", 8, "bold"),
            wraplength=175,
        )
        self.rotation_label.pack(anchor="w", pady=(5, 2))

        ttk.Label(
            landmark_panel,
            text="Select a landmark to place or replace it once.",
            wraplength=175,
            foreground=GUI_MUTED_FG,
        ).pack(anchor="w", fill="x", pady=(1, 4))

        ttk.Separator(landmark_panel, orient="horizontal").pack(
            fill="x", pady=(1, 3)
        )

        self.landmark_status_label = ttk.Label(
            landmark_panel,
            text="",
            wraplength=175,
            foreground=GUI_MUTED_FG,
        )
        self.landmark_status_label.pack(anchor="w", fill="x")

        # CENTER: preview and compact histogram
        center = ttk.Frame(body)
        center.pack(side="left", fill="both", expand=True)

        self.preview_canvas = tk.Canvas(
            center,
            background="black",
            highlightthickness=1,
            highlightbackground=GUI_BORDER,
            cursor=self.placement_cursor,
        )
        self.preview_canvas.pack(fill="both", expand=True)

        self.preview_canvas.bind("<ButtonPress-1>", self.on_preview_button_press)
        self.preview_canvas.bind("<B1-Motion>", self.on_preview_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self.on_preview_button_release)
        self.preview_canvas.bind("<Configure>", self.on_preview_canvas_resize)
        self.preview_canvas.bind("<MouseWheel>", self.on_preview_mousewheel)
        self.preview_canvas.bind("<Button-4>", self.on_preview_mousewheel)
        self.preview_canvas.bind("<Button-5>", self.on_preview_mousewheel)
        self.preview_canvas.bind("<ButtonPress-3>", self.on_preview_pan_press)
        self.preview_canvas.bind("<B3-Motion>", self.on_preview_pan_drag)
        self.preview_canvas.bind("<ButtonRelease-3>", self.on_preview_pan_release)
        self.preview_canvas.bind("<Double-Button-3>", self.on_preview_zoom_reset)

        self.hist_canvas = tk.Canvas(
            center,
            height=46,
            background=GUI_PANEL_BG,
            highlightthickness=1,
            highlightbackground=GUI_BORDER,
        )
        self.hist_canvas.pack(fill="x", pady=(3, 0))

        # RIGHT RAIL: Cellpose + preview controls + branding
        tools = ttk.Frame(body, width=205)
        self.right_panel = tools
        tools.pack(side="right", fill="y", padx=(5, 0))
        tools.pack_propagate(False)

        ttk.Label(
            tools,
            text="CELLPOSE",
            font=("TkDefaultFont", 9, "bold"),
            foreground=GUI_MUTED_FG,
        ).pack(anchor="w", pady=(1, 3))

        self.test_cellpose_button = ttk.Button(
            tools,
            text="Test Cellpose",
            command=self.test_cellpose,
        )
        self.test_cellpose_button.pack(fill="x", pady=(0, 2))

        self.test_progress = ttk.Progressbar(tools, mode="indeterminate")
        self.test_progress.pack(fill="x", pady=(1, 2))

        self.test_busy_label = ttk.Label(
            tools,
            text="",
            wraplength=195,
            foreground=GUI_MUTED_FG,
        )
        self.test_busy_label.pack(anchor="w", fill="x", pady=(0, 2))

        self.cellpose_preview_toggle = ttk.Checkbutton(
            tools,
            text="Show Cellpose preview",
            variable=self.show_cellpose_preview_var,
            command=self.toggle_cellpose_preview,
        )
        self.cellpose_preview_toggle.pack(anchor="w", pady=(1, 3))

        self.test_label = ttk.Label(
            tools,
            text="Exact displayed exposure; Cellpose normalization OFF.",
            wraplength=195,
            foreground=GUI_MUTED_FG,
        )
        self.test_label.pack(anchor="w", fill="x", pady=(0, 5))

        ttk.Separator(tools, orient="horizontal").pack(fill="x", pady=3)

        ttk.Label(
            tools,
            text="CUSTOM COUNTING ROI",
            font=("TkDefaultFont", 9, "bold"),
            foreground=GUI_MUTED_FG,
        ).pack(anchor="w", pady=(1, 3))

        self.custom_roi_exclusion_toggle = ttk.Checkbutton(
            tools,
            text="Exclusion mode (ignore inside ROI)",
            variable=self.custom_roi_exclusion_var,
            command=self._on_custom_roi_mode_changed,
        )
        self.custom_roi_exclusion_toggle.pack(anchor="w", pady=(0, 4))

        roi_draw_row = ttk.Frame(tools)
        roi_draw_row.pack(fill="x", pady=(0, 3))
        self.custom_roi_draw_buttons = {}
        for hemisphere in ("L", "R"):
            button = ttk.Button(
                roi_draw_row,
                text=f"Draw {hemisphere} ROI",
                command=lambda h=hemisphere: self.start_custom_roi_draw(h),
            )
            button.pack(
                side="left",
                fill="x",
                expand=True,
                padx=((0, 2) if hemisphere == "L" else (2, 0)),
            )
            self.custom_roi_draw_buttons[hemisphere] = button

        roi_clear_row = ttk.Frame(tools)
        roi_clear_row.pack(fill="x", pady=(0, 2))
        self.custom_roi_clear_buttons = {}
        for hemisphere in ("L", "R"):
            button = ttk.Button(
                roi_clear_row,
                text=f"Clear {hemisphere}",
                command=lambda h=hemisphere: self.clear_custom_roi(h),
            )
            button.pack(
                side="left",
                fill="x",
                expand=True,
                padx=((0, 2) if hemisphere == "L" else (2, 0)),
            )
            self.custom_roi_clear_buttons[hemisphere] = button

        self.custom_roi_status_label = ttk.Label(
            tools,
            text="",
            wraplength=195,
            foreground=GUI_MUTED_FG,
        )
        self.custom_roi_status_label.pack(anchor="w", fill="x", pady=(1, 4))
        self._update_custom_roi_controls()

        ttk.Separator(tools, orient="horizontal").pack(fill="x", pady=3)

        ttk.Label(
            tools,
            text="PREVIEW",
            font=("TkDefaultFont", 9, "bold"),
            foreground=GUI_MUTED_FG,
        ).pack(anchor="w", pady=(1, 2))

        ttk.Label(
            tools,
            text=(
                "Wheel — zoom\n"
                "Right-drag — pan\n"
                "Double right-click — fit"
            ),
            foreground=GUI_MUTED_FG,
            wraplength=195,
        ).pack(anchor="w")

        ttk.Label(
            tools,
            text="Save requires all landmarks on every image.",
            foreground=GUI_MUTED_FG,
            wraplength=195,
        ).pack(anchor="w", pady=(7, 3))

        if self.logo_video_capture is not None or self.banner_source_image is not None:
            banner_footer = tk.Frame(tools, background=GUI_BG)
            banner_footer.pack(side="bottom", fill="x", pady=(6, 4))

            self.banner_label = tk.Label(
                banner_footer,
                background=GUI_BG,
                borderwidth=0,
                highlightthickness=0,
            )
            self.banner_label.pack(anchor="center")

            tools.bind("<Configure>", self._on_right_panel_configure)

            if self.logo_video_capture is not None:
                self._start_logo_video()
            else:
                self._refresh_banner_image()

        self.root.bind("<Return>", lambda event: self.accept())


    # ------------------------------------------------------------------
    # Data / exposure state
    # ------------------------------------------------------------------

    def _cache_mip(self, key, mip):
        self.mip_cache[key] = mip
        try:
            self.mip_cache_order.remove(key)
        except ValueError:
            pass
        self.mip_cache_order.append(key)

        while len(self.mip_cache_order) > self.max_cache_items:
            old = self.mip_cache_order.pop(0)
            self.mip_cache.pop(old, None)

    def _submit_mip(self, file_index, channel):
        key = (int(file_index), str(channel))
        if key in self.mip_cache or key in self.mip_futures:
            return
        self.mip_futures[key] = self.mip_executor.submit(
            read_mip_for_file_channel,
            self.ims_files[int(file_index)],
            str(channel),
        )

    def _get_mip(
        self,
        file_index,
        channel,
    ):
        key = (int(file_index), str(channel))

        if key in self.mip_cache:
            try:
                self.mip_cache_order.remove(key)
            except ValueError:
                pass
            self.mip_cache_order.append(key)
            return self.mip_cache[key]

        self._submit_mip(file_index, channel)
        return _MIP_LOADING

    def _schedule_mip_poll(self):
        if self._mip_poll_after_id is not None:
            return
        self._mip_poll_after_id = self.root.after(
            50,
            self._poll_mip_futures,
        )

    def _poll_mip_futures(self):
        self._mip_poll_after_id = None
        current_key = (int(self.current_file_index), str(self.current_channel))
        current_finished = False

        for key, future in list(self.mip_futures.items()):
            if not future.done():
                continue
            self.mip_futures.pop(key, None)
            try:
                mip = future.result()
            except Exception as exc:
                print(
                    f"GUI MIP load failed for "
                    f"{self.ims_files[key[0]].name} / {key[1]}: {exc}"
                )
                mip = None
            self._cache_mip(key, mip)
            if key == current_key:
                current_finished = True

        if current_finished:
            self.refresh_preview()
            if GUI_PRELOAD_ALL_MIPS:
                self._prefetch_all_mips()
            else:
                self._prefetch_nearby_mips()

        try:
            if self.root.winfo_exists():
                self._schedule_mip_poll()
        except Exception:
            pass

    def _prefetch_nearby_mips(self):
        """Use spare RAM/worker capacity to warm likely next previews."""
        i = int(self.current_file_index)
        # Other channels from the current image are the most likely next clicks.
        for channel in CHANNEL_PROCESSING_ORDER:
            self._submit_mip(i, channel)

        # Also warm the current channel for adjacent images.
        if len(self.ims_files) > 1:
            self._submit_mip((i + 1) % len(self.ims_files), self.current_channel)
            self._submit_mip((i - 1) % len(self.ims_files), self.current_channel)

    def _prefetch_all_mips(self):
        """Warm every image/channel MIP in the background.

        This workstation has enough RAM to keep the whole GUI working set
        resident. Missing channels simply resolve to None and are cached too,
        so revisiting them also becomes instantaneous.
        """
        for file_index in range(len(self.ims_files)):
            for channel in CHANNEL_PROCESSING_ORDER:
                self._submit_mip(file_index, channel)

    def _find_first_available_mip(
        self,
        channel,
    ):
        """Synchronously obtain one MIP for initial exposure calibration only.

        This runs before the Tk mainloop starts. The result is immediately put
        into the large GUI cache; subsequent image/channel navigation is async.
        """
        for i in range(len(self.ims_files)):
            key = (int(i), str(channel))
            if key in self.mip_cache:
                mip = self.mip_cache[key]
            else:
                mip = read_mip_for_file_channel(
                    self.ims_files[i],
                    channel,
                )
                self._cache_mip(key, mip)

            if mip is not None:
                return i, mip

        return None, None

    def _initialize_channel_baselines(
        self,
    ):
        total = len(CHANNEL_PROCESSING_ORDER)
        for position, channel in enumerate(CHANNEL_PROCESSING_ORDER, start=1):
            if self.loading_callback is not None:
                self.loading_callback(
                    f"Loading preview channel {channel}",
                    f"Reading initial IMS preview {position} of {total}.",
                    position - 1,
                    total,
                )
            _, mip = self._find_first_available_mip(
                channel
            )

            if mip is None:
                self.channel_baseline[
                    channel
                ] = {
                    "black": 0.0,
                    "white": 1.0,
                    "slider_max": 1.0,
                }
                continue

            (
                black,
                white,
                slider_max,
            ) = suggest_exposure_from_mip(
                mip
            )

            previous = self.previous.get(
                channel,
                {},
            )

            if (
                "black" in previous
                and "white" in previous
            ):
                prev_black = float(
                    previous[
                        "black"
                    ]
                )
                prev_white = float(
                    previous[
                        "white"
                    ]
                )

                if prev_white > prev_black:
                    black = prev_black
                    white = prev_white
                    slider_max = max(
                        slider_max,
                        white,
                    )

            self.channel_baseline[
                channel
            ] = {
                "black": float(
                    black
                ),
                "white": float(
                    white
                ),
                "slider_max": float(
                    slider_max
                ),
            }

    def _series_average(
        self,
        channel,
    ):
        values = [
            value
            for (
                file_index,
                ch
            ), value in self.image_exposure_overrides.items()
            if ch == channel
        ]

        if not values:
            baseline = self.channel_baseline[
                channel
            ]
            return {
                "black": float(
                    baseline[
                        "black"
                    ]
                ),
                "white": float(
                    baseline[
                        "white"
                    ]
                ),
            }

        return {
            "black": float(
                np.mean(
                    [
                        v[
                            "black"
                        ]
                        for v in values
                    ]
                )
            ),
            "white": float(
                np.mean(
                    [
                        v[
                            "white"
                        ]
                        for v in values
                    ]
                )
            ),
        }

    def _effective_exposure(
        self,
        file_index,
        channel,
    ):
        key = (
            int(
                file_index
            ),
            str(
                channel
            ),
        )

        if key in self.image_exposure_overrides:
            value = self.image_exposure_overrides[
                key
            ]
            return {
                "black": float(
                    value[
                        "black"
                    ]
                ),
                "white": float(
                    value[
                        "white"
                    ]
                ),
                "source": "individual",
            }

        average = self._series_average(
            channel
        )

        return {
            "black": float(
                average[
                    "black"
                ]
            ),
            "white": float(
                average[
                    "white"
                ]
            ),
            "source": "series_average",
        }

    def _load_effective_exposure_into_sliders(
        self,
    ):
        self.loading_sliders = True

        try:
            effective = self._effective_exposure(
                self.current_file_index,
                self.current_channel,
            )

            baseline = self.channel_baseline[
                self.current_channel
            ]

            slider_max = max(
                1.0,
                float(
                    baseline[
                        "slider_max"
                    ]
                ),
                float(
                    effective[
                        "white"
                    ]
                ),
            )

            resolution = (
                float(GUI_EXPOSURE_FINE_RESOLUTION)
                if slider_max > 20
                else 0.01
            )

            for scale in (
                self.black_scale,
                self.white_scale,
            ):
                scale.configure(
                    from_=0.0,
                    to=slider_max,
                    resolution=resolution,
                )

            self.black_var.set(
                float(
                    effective[
                        "black"
                    ]
                )
            )
            self.white_var.set(
                float(
                    effective[
                        "white"
                    ]
                )
            )

        finally:
            self.loading_sliders = False

    def _mark_current_exposure_override(
        self,
    ):
        key = (
            int(
                self.current_file_index
            ),
            str(
                self.current_channel
            ),
        )

        self.image_exposure_overrides[
            key
        ] = {
            "black": float(
                self.black_var.get()
            ),
            "white": float(
                self.white_var.get()
            ),
        }


    def _landmarks_complete_for_current_image(
        self,
    ):
        placed = self.manual_landmarks_yx[
            self.current_file_index
        ]
        return all(
            key in placed
            for key in MANUAL_GUI_LANDMARKS
        )

    def _current_exposure_key(self):
        return (int(self.current_file_index), str(self.current_channel))

    def _finish_exposure_setup(self, clear_picks=False):
        """Leave temporary preview mode and retain the effective exposure."""
        key = self._current_exposure_key()
        self.exposure_finalized_keys.add(key)
        if clear_picks:
            self.exposure_calibration_picks.pop(key, None)
        self.exposure_pick_mode = None
        self._update_exposure_pick_button_styles()
        self._update_preview_cursor()

    def _exposure_setup_is_complete(self, file_index=None, channel=None):
        key = (
            int(self.current_file_index if file_index is None else file_index),
            str(self.current_channel if channel is None else channel),
        )
        if key in self.exposure_finalized_keys:
            return True
        picks = self.exposure_calibration_picks.get(key, {})
        return "positive" in picks and "background" in picks

    def _use_forced_black_preview_mode(
        self,
    ):
        """
        Temporary display-only mode:
        - on the first (g) channel while drawing landmarks for an image
        - on any channel while an exposure calibration picker is active

        This does NOT change the saved exposure semantics. It uses black zero
        and an adaptive bright white point so the tissue outline stays visible.
        """
        if self.exposure_pick_mode is not None:
            return True

        if self._exposure_setup_is_complete():
            return False

        return (
            str(self.current_channel)
            == CHANNEL_PROCESSING_ORDER[0]
            and not self._landmarks_complete_for_current_image()
        )

    def _preview_black_white(
        self,
        mip=None,
    ):
        slider_black = float(
            self.black_var.get()
        )
        slider_white = float(
            self.white_var.get()
        )

        if self._use_forced_black_preview_mode():
            if mip is None or mip is _MIP_LOADING:
                preview_white = float(SETUP_PREVIEW_WHITE_MIN)
            else:
                preview_white = suggest_setup_preview_white(mip)
            return (
                float(SETUP_PREVIEW_BLACK),
                preview_white,
                True,
                slider_black,
                slider_white,
            )

        return (
            slider_black,
            slider_white,
            False,
            slider_black,
            slider_white,
        )

    def _reset_landmark_for_new_image(self):
        self._cancel_midline_drag()
        placed = self.manual_landmarks_yx[self.current_file_index]
        first_missing = next(
            (key for key in MANUAL_GUI_LANDMARKS if key not in placed),
            None,
        )
        self.landmark_sequence_active = first_missing is not None
        self.landmark_var.set(first_missing or "")
        self.current_landmark = first_missing
        self._update_landmark_button_styles()
        self._update_preview_cursor()

    def load_window_settings_json(self):
        """Load exposures and landmarks from a saved Neurodot settings JSON."""
        import json

        selected_path = self.filedialog.askopenfilename(
            parent=self.root,
            title="Load Cellpose window settings",
            initialdir=str(EXPOSURE_SETTINGS_JSON.parent),
            filetypes=[
                ("JSON settings", "*.json"),
                ("All files", "*.*"),
            ],
        )

        if not selected_path:
            return

        path = Path(selected_path)

        try:
            payload = json.loads(
                path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            self.messagebox.showerror(
                "Could not load settings",
                f"Could not read {path.name}:\n\n{exc}",
            )
            return

        series_average = payload.get(
            "series_average",
            payload.get("channels", {}),
        )
        per_file = payload.get(
            "per_file",
            {},
        )
        saved_landmarks = payload.get(
            "manual_landmarks_yx",
            {},
        )
        saved_custom_rois = payload.get(
            "custom_counting_rois_yx",
            {},
        )
        saved_custom_roi_modes = payload.get(
            "custom_counting_roi_modes",
            {},
        )

        saved_enabled_channels = payload.get(
            "enabled_channels",
            None,
        )
        if isinstance(saved_enabled_channels, (list, tuple, set)):
            enabled_set = {
                str(channel)
                for channel in saved_enabled_channels
                if str(channel) in CHANNEL_PROCESSING_ORDER
            }
            for channel in CHANNEL_PROCESSING_ORDER:
                var = self.channel_enabled_vars.get(channel)
                if var is not None:
                    var.set(channel in enabled_set)
            self._update_channel_count_button_styles()

        # Current settings store one series-wide choice per channel. Also
        # accept the early single-string form for backward compatibility.
        saved_counting_regions = payload.get(
            "counting_regions",
            payload.get("counting_region", DEFAULT_COUNTING_REGION),
        )
        if isinstance(saved_counting_regions, dict):
            for channel in CHANNEL_PROCESSING_ORDER:
                region = str(
                    saved_counting_regions.get(channel, DEFAULT_COUNTING_REGION)
                ).strip().lower()
                if region in COUNTING_REGION_MODES:
                    self.channel_counting_regions[channel] = region
        else:
            region = str(saved_counting_regions).strip().lower()
            if region in COUNTING_REGION_MODES:
                for channel in CHANNEL_PROCESSING_ORDER:
                    self.channel_counting_regions[channel] = region

        self.counting_region_var.set(
            self.channel_counting_regions[self.current_channel]
        )
        self._update_counting_region_button_styles()

        # Restore channel baselines first. This also supports older JSON files
        # that contained only the historical "channels" section.
        loaded_baselines = 0
        for channel in CHANNEL_PROCESSING_ORDER:
            value = series_average.get(channel, {})
            try:
                black = float(value["black"])
                white = float(value["white"])
            except Exception:
                continue

            if white <= black:
                continue

            baseline = self.channel_baseline[channel]
            baseline["black"] = black
            baseline["white"] = white
            baseline["slider_max"] = max(
                float(baseline.get("slider_max", 1.0)),
                white,
            )
            loaded_baselines += 1

        # Reconstruct explicit per-image overrides using file names. Values
        # tagged "series_average" remain unset so the original fallback
        # semantics are preserved.
        self.image_exposure_overrides.clear()
        loaded_exposure_overrides = 0

        current_name_to_index = {
            path.name: i
            for i, path in enumerate(self.ims_files)
        }

        for file_name, channels in per_file.items():
            if file_name not in current_name_to_index:
                continue

            file_index = current_name_to_index[file_name]

            for channel in CHANNEL_PROCESSING_ORDER:
                value = channels.get(channel, {})
                if not isinstance(value, dict):
                    continue

                if str(value.get("source", "individual")) != "individual":
                    continue

                try:
                    black = float(value["black"])
                    white = float(value["white"])
                except Exception:
                    continue

                if white <= black:
                    continue

                self.image_exposure_overrides[
                    (file_index, channel)
                ] = {
                    "black": black,
                    "white": white,
                }
                loaded_exposure_overrides += 1

        # Restore all manual landmarks, including rot_bottom and rot_top. The
        # saved rotation value itself need not be loaded because it is derived
        # deterministically from those two midline landmarks.
        loaded_landmarks = 0
        matched_landmark_files = 0

        for file_name, landmarks in saved_landmarks.items():
            if file_name not in current_name_to_index:
                continue
            if not isinstance(landmarks, dict):
                continue

            file_index = current_name_to_index[file_name]
            restored = {}

            for key in MANUAL_GUI_LANDMARKS:
                yx = landmarks.get(key)
                try:
                    if len(yx) != 2:
                        continue
                    y = float(yx[0])
                    x = float(yx[1])
                except Exception:
                    continue

                restored[key] = [y, x]
                loaded_landmarks += 1

            if restored:
                self.manual_landmarks_yx[file_index] = restored
                matched_landmark_files += 1

        self.custom_counting_rois_yx.clear()
        self.custom_counting_roi_modes.clear()
        loaded_custom_rois = 0
        if isinstance(saved_custom_rois, dict):
            for file_name, channel_polygons in saved_custom_rois.items():
                if file_name not in current_name_to_index:
                    continue
                if not isinstance(channel_polygons, dict):
                    continue
                file_index = current_name_to_index[file_name]
                for channel in CHANNEL_PROCESSING_ORDER:
                    saved_channel_roi = channel_polygons.get(channel)
                    if isinstance(saved_channel_roi, dict):
                        hemisphere_polygons = saved_channel_roi
                    elif isinstance(saved_channel_roi, (list, tuple)):
                        # Backward compatibility: the initial one-ROI format
                        # is applied to both hemispheres, where the normal L/R
                        # split clips it to the relevant side.
                        hemisphere_polygons = {
                            "L": saved_channel_roi,
                            "R": saved_channel_roi,
                        }
                    else:
                        continue

                    for hemisphere in ("L", "R"):
                        polygon = hemisphere_polygons.get(hemisphere)
                        if not isinstance(polygon, (list, tuple)):
                            continue
                        restored_polygon = []
                        for yx in polygon:
                            try:
                                if len(yx) != 2:
                                    continue
                                restored_polygon.append([
                                    float(yx[0]),
                                    float(yx[1]),
                                ])
                            except Exception:
                                continue
                        if len(restored_polygon) >= CUSTOM_ROI_MIN_VERTICES:
                            roi_key = (file_index, channel, hemisphere)
                            self.custom_counting_rois_yx[roi_key] = restored_polygon
                            try:
                                restored_mode = str(
                                    saved_custom_roi_modes[file_name][channel][hemisphere]
                                ).strip().lower()
                            except Exception:
                                restored_mode = DEFAULT_CUSTOM_ROI_MODE
                            if restored_mode not in CUSTOM_ROI_MODES:
                                restored_mode = DEFAULT_CUSTOM_ROI_MODE
                            self.custom_counting_roi_modes[roi_key] = restored_mode
                            loaded_custom_rois += 1

        # A loaded JSON represents deliberate exposure choices, so browsing
        # restored channels must show their true effective exposure.
        self.exposure_finalized_keys = {
            (file_index, channel)
            for file_index in range(len(self.ims_files))
            for channel in CHANNEL_PROCESSING_ORDER
        }
        self.exposure_pick_mode = None
        self._update_exposure_pick_button_styles()

        self._load_effective_exposure_into_sliders()
        self._reset_landmark_for_new_image()
        self._update_custom_roi_controls()
        self.refresh_preview()

        self.messagebox.showinfo(
            "Settings loaded",
            (
                f"Loaded {path.name}.\n\n"
                f"Channel exposure baselines: {loaded_baselines}\n"
                f"Individual image/channel exposures: "
                f"{loaded_exposure_overrides}\n"
                f"Images with restored landmarks: "
                f"{matched_landmark_files}\n"
                f"Landmark points restored: {loaded_landmarks}\n\n"
                f"Custom counting ROIs: {loaded_custom_rois}\n"
                "Counting regions: "
                + ", ".join(
                    f"{channel}={self.channel_counting_regions[channel]}"
                    for channel in CHANNEL_PROCESSING_ORDER
                )
                + "\n\n"
                "Midline points are included in the landmark data; rotation "
                "and anatomical counting regions are recalculated automatically."
            ),
        )


    # ------------------------------------------------------------------
    # Exposure calibration pickers
    # ------------------------------------------------------------------

    def _ensure_exposure_slider_range(self, value):
        current_max = max(
            float(self.black_scale.cget("to")),
            float(self.white_scale.cget("to")),
        )
        if float(value) <= current_max:
            return

        new_max = max(
            float(value) * 1.10,
            float(value) + 1.0,
        )
        self.black_scale.configure(to=new_max)
        self.white_scale.configure(to=new_max)


    def _update_exposure_pick_button_styles(self):
        """Green-border the calibration step currently waiting for a click."""
        button_by_mode = {
            "background": self.pick_background_button,
            "positive": self.pick_positive_button,
        }

        for mode, button in button_by_mode.items():
            try:
                button.configure(
                    style=(
                        "ActiveChannel.TButton"
                        if self.exposure_pick_mode == mode
                        else "Channel.TButton"
                    )
                )
            except Exception:
                pass


    def _set_exposure_pick_mode(self, mode):
        if mode not in ("background", "positive"):
            raise ValueError(mode)

        self._cancel_midline_drag()
        if self._landmarks_complete_for_current_image():
            self.landmark_sequence_active = False
            self.landmark_var.set("")
            self.current_landmark = None
            self._update_landmark_button_styles()
        self.exposure_pick_mode = mode
        self._update_exposure_pick_button_styles()

        if mode == "background":
            message = (
                f"BACKGROUND PICK ACTIVE — click a background region. "
                f"Preview temporarily uses black=0 and an adaptive "
                f"white={SETUP_PREVIEW_WHITE_MIN:.0f}-"
                f"{SETUP_PREVIEW_WHITE_MAX:.0f} for visibility. "
                f"Brightest raw pixel inside the {EXPOSURE_PICK_RADIUS_PX}px "
                f"radius circle becomes the saved black point."
            )
        else:
            message = (
                f"WEAKEST POSITIVE PICK ACTIVE — click a weak true-positive "
                f"while preview uses black=0 and an adaptive bright white. "
                f"Brightest raw pixel "
                f"inside the {EXPOSURE_PICK_RADIUS_PX}px radius circle plus "
                f"headroom becomes the saved white point."
            )

        self.exposure_pick_status_label.configure(text=message)
        self._update_preview_cursor()


    def clear_exposure_calibration_picks(self):
        key = (
            int(self.current_file_index),
            str(self.current_channel),
        )
        self.exposure_calibration_picks.pop(key, None)
        self.exposure_pick_mode = None
        self._update_exposure_pick_button_styles()
        self._update_preview_cursor()
        self.exposure_pick_status_label.configure(
            text=(
                f"Calibration markers cleared. Order: weakest positive, "
                f"then brightest background "
                f"(sample radius {EXPOSURE_PICK_RADIUS_PX}px)."
            )
        )
        self.refresh_preview()


    def _sample_raw_mip_circle(self, mip, center_y, center_x):
        """Find the true brightest raw MIP pixel inside the selected circle."""
        arr = np.asarray(mip, dtype=np.float32)
        h, w = arr.shape
        radius = float(EXPOSURE_PICK_RADIUS_PX)

        y0 = max(0, int(math.floor(center_y - radius)))
        y1 = min(h, int(math.ceil(center_y + radius)) + 1)
        x0 = max(0, int(math.floor(center_x - radius)))
        x1 = min(w, int(math.ceil(center_x + radius)) + 1)

        patch = arr[y0:y1, x0:x1]

        yy, xx = np.ogrid[y0:y1, x0:x1]
        circle = (
            (yy - float(center_y)) ** 2
            + (xx - float(center_x)) ** 2
            <= radius ** 2
        )
        valid = circle & np.isfinite(patch)

        if not np.any(valid):
            raise ValueError(
                "No finite image pixels were found inside the sampling circle."
            )

        masked = np.where(valid, patch, -np.inf)
        flat_index = int(np.argmax(masked))
        local_y, local_x = np.unravel_index(
            flat_index,
            masked.shape,
        )

        value = float(masked[local_y, local_x])
        bright_y = int(y0 + local_y)
        bright_x = int(x0 + local_x)

        finite_values = patch[valid]
        p999 = float(
            np.percentile(
                finite_values,
                99.9,
            )
        )

        return {
            "value": value,
            "bright_y": bright_y,
            "bright_x": bright_x,
            "p999": p999,
            "center_y": float(center_y),
            "center_x": float(center_x),
            "radius_px": radius,
        }


    def _apply_exposure_calibration_pick(self, event):
        mode = self.exposure_pick_mode
        if mode not in ("background", "positive"):
            return False

        yx = self._canvas_event_to_native_yx(event)
        if yx is None:
            return True

        y, x = yx
        mip = self._get_mip(
            self.current_file_index,
            self.current_channel,
        )

        if mip is _MIP_LOADING:
            self.messagebox.showinfo(
                "Image still loading",
                "Wait for this channel's full-resolution MIP to finish loading.",
            )
            return True

        if mip is None:
            self.messagebox.showwarning(
                "Channel unavailable",
                f"{self.current_channel!r} is not present in this image.",
            )
            self.exposure_pick_mode = None
            return True

        try:
            sample = self._sample_raw_mip_circle(
                mip,
                y,
                x,
            )
        except Exception as exc:
            self.messagebox.showerror(
                "Exposure sampling failed",
                str(exc),
            )
            self.exposure_pick_mode = None
            return True

        value = float(sample["value"])

        key = (
            int(self.current_file_index),
            str(self.current_channel),
        )
        picks = self.exposure_calibration_picks.setdefault(
            key,
            {},
        )
        picks[mode] = sample

        if mode == "background":
            self._ensure_exposure_slider_range(value)

            self.loading_sliders = True
            try:
                self.black_var.set(round(value, 4))

                # Keep the image renderable between the two calibration picks.
                if float(self.white_var.get()) <= value:
                    self.white_var.set(
                        round(
                            value + max(
                                1.0,
                                0.10 * max(value, 1.0),
                            ),
                            4,
                        )
                    )
            finally:
                self.loading_sliders = False

            self._mark_current_exposure_override()

            diagnostic = ""
            if sample["p999"] > 0 and value > 1.5 * sample["p999"]:
                diagnostic = (
                    " Possible hot-pixel outlier: max is much brighter than "
                    "the circle's 99.9th percentile."
                )

            self.exposure_pick_status_label.configure(
                text=(
                    f"Background: brightest={value:.2f}, "
                    f"p99.9={sample['p999']:.2f} → black={value:.2f}."
                    f"{diagnostic}"
                )
            )

        else:
            black = float(self.black_var.get())

            if value <= black:
                self.exposure_pick_mode = "positive"
                self._update_exposure_pick_button_styles()
                self.exposure_pick_status_label.configure(
                    text=(
                        f"Positive maximum {value:.2f} is not above current "
                        f"black {black:.2f}. Pick another positive cell or "
                        f"recalibrate the background first. "
                        f"Weakest-positive selection remains active."
                    )
                )
                self.refresh_preview()
                return True

            signal_span = value - black
            headroom = max(
                float(EXPOSURE_POSITIVE_HEADROOM_MIN_RAW),
                float(EXPOSURE_POSITIVE_HEADROOM_FRACTION) * signal_span,
            )
            white = value + headroom

            self._ensure_exposure_slider_range(white)

            self.loading_sliders = True
            try:
                self.white_var.set(round(white, 4))
            finally:
                self.loading_sliders = False

            self._mark_current_exposure_override()

            self.exposure_pick_status_label.configure(
                text=(
                    f"Weak positive: brightest={value:.2f}, "
                    f"p99.9={sample['p999']:.2f}; "
                    f"headroom={headroom:.2f} → white={white:.2f}."
                )
            )

        # Sequential calibration workflow:
        #   final landmark/channel switch -> positive click -> background click -> done.
        if mode == "positive":
            self._set_exposure_pick_mode("background")
        else:
            if "positive" in picks and "background" in picks:
                self._finish_exposure_setup(clear_picks=False)
            else:
                self.exposure_pick_mode = None
                self._update_exposure_pick_button_styles()
                self._update_preview_cursor()

        self.refresh_preview()
        return True


    # ------------------------------------------------------------------
    # Navigation / exposure actions
    # ------------------------------------------------------------------

    def _update_channel_button_styles(self):
        """Give the currently displayed fluorescence channel a green border."""
        for name, button in self.channel_buttons.items():
            try:
                button.configure(
                    style=(
                        "ActiveChannel.TButton"
                        if name == self.current_channel
                        else "Channel.TButton"
                    )
                )
            except Exception:
                pass

    def _update_channel_count_button_styles(self):
        """Show enabled counting channels as green-outlined segments."""
        if not hasattr(self, "channel_count_buttons"):
            return
        for channel, button in self.channel_count_buttons.items():
            enabled = bool(self.channel_enabled_vars[channel].get())
            outline = GUI_ACCENT if enabled else GUI_BORDER
            self.channel_count_borders[channel].configure(
                background=outline
            )
            button.configure(
                background=GUI_CONTROL_BG,
                selectcolor=GUI_CONTROL_BG,
                foreground=(GUI_FG if enabled else GUI_MUTED_FG),
            )

            display_button = self.channel_buttons.get(channel)
            if display_button is not None:
                try:
                    display_button.state(
                        ["!disabled"] if enabled else ["disabled"]
                    )
                except Exception:
                    pass

    def _enabled_preview_channels(self):
        return [
            channel
            for channel in CHANNEL_PROCESSING_ORDER
            if bool(self.channel_enabled_vars[channel].get())
        ]

    def _next_enabled_channel(self, current_channel):
        enabled = self._enabled_preview_channels()
        if not enabled:
            return None
        try:
            start = CHANNEL_PROCESSING_ORDER.index(current_channel)
        except ValueError:
            return enabled[0]
        for offset in range(1, len(CHANNEL_PROCESSING_ORDER) + 1):
            candidate = CHANNEL_PROCESSING_ORDER[
                (start + offset) % len(CHANNEL_PROCESSING_ORDER)
            ]
            if candidate in enabled:
                return candidate
        return enabled[0]

    def _on_channel_count_changed(self):
        """Keep disabled production channels out of preview navigation."""
        self._update_channel_count_button_styles()
        enabled = self._enabled_preview_channels()

        if self.current_channel not in enabled:
            next_channel = self._next_enabled_channel(self.current_channel)
            if next_channel is not None:
                self.set_channel(next_channel)
                return

        self.refresh_preview()

    def _update_counting_region_button_styles(self):
        """Show the selected anatomical area as a green-outlined segment."""
        if not hasattr(self, "counting_region_buttons"):
            return
        selected = str(self.counting_region_var.get()).strip().lower()
        for region, button in self.counting_region_buttons.items():
            active = region == selected
            outline = GUI_ACCENT if active else GUI_BORDER
            self.counting_region_borders[region].configure(
                background=outline
            )
            button.configure(
                background=GUI_CONTROL_BG,
                selectcolor=GUI_CONTROL_BG,
                foreground=(GUI_FG if active else GUI_MUTED_FG),
            )

    def _on_counting_region_changed(self):
        """Store the selected region for the currently displayed channel."""
        region = str(self.counting_region_var.get()).strip().lower()
        if region not in COUNTING_REGION_MODES:
            region = DEFAULT_COUNTING_REGION
            self.counting_region_var.set(region)
        self.channel_counting_regions[self.current_channel] = region
        self._update_counting_region_button_styles()
        self.refresh_preview()

    def set_channel(
        self,
        channel,
    ):
        if (
            hasattr(self, "channel_enabled_vars")
            and channel in self.channel_enabled_vars
            and not bool(self.channel_enabled_vars[channel].get())
        ):
            return
        self._cancel_custom_roi_draft(deactivate=True)
        self.current_channel = channel
        self.counting_region_label.configure(
            text="COUNT AREA"
        )
        self.counting_region_var.set(
            self.channel_counting_regions.get(
                channel,
                DEFAULT_COUNTING_REGION,
            )
        )
        self._update_counting_region_button_styles()
        self._update_channel_button_styles()
        self._load_effective_exposure_into_sliders()

        # Untouched channels enter calibration automatically. Completed work
        # displays the true effective exposure when revisited.
        if self._exposure_setup_is_complete():
            self.exposure_pick_mode = None
            self._update_exposure_pick_button_styles()
            self._update_preview_cursor()
        else:
            self._set_exposure_pick_mode("positive")
        self._update_custom_roi_controls()

        self.refresh_preview()

    def previous_file(
        self,
    ):
        self._cancel_custom_roi_draft(deactivate=True)
        self.exposure_pick_mode = None
        self._update_exposure_pick_button_styles()

        self.current_file_index = (
            self.current_file_index
            - 1
        ) % len(
            self.ims_files
        )

        self._load_effective_exposure_into_sliders()
        self._reset_landmark_for_new_image()
        self._reset_preview_view(refresh=False)
        self._update_custom_roi_controls()
        self.exposure_pick_status_label.configure(
            text=(
                "Landmark drawing mode: on the first channel (g), preview black "
                "is temporarily 0 and preview white adapts within 200-400."
            )
        )
        self.refresh_preview()

    def next_file(
        self,
    ):
        self._cancel_custom_roi_draft(deactivate=True)
        self.exposure_pick_mode = None
        self._update_exposure_pick_button_styles()

        self.current_file_index = (
            self.current_file_index
            + 1
        ) % len(
            self.ims_files
        )

        # Start each new image on the first enabled logical channel. Disabled
        # production channels are never brought back into the preview.
        enabled_preview_channels = self._enabled_preview_channels()
        if enabled_preview_channels:
            self.current_channel = enabled_preview_channels[0]
        self.counting_region_label.configure(
            text="COUNT AREA"
        )
        self.counting_region_var.set(
            self.channel_counting_regions[self.current_channel]
        )
        self._update_counting_region_button_styles()
        self._update_channel_button_styles()

        self._load_effective_exposure_into_sliders()
        self._reset_landmark_for_new_image()
        self._reset_preview_view(refresh=False)
        self._update_custom_roi_controls()
        self.exposure_pick_status_label.configure(
            text=(
                "Landmark drawing mode: on the first channel (g), preview black "
                "is temporarily 0 and preview white adapts within 200-400."
            )
        )
        self.refresh_preview()

    def _nudge_exposure(
        self,
        which,
        delta,
    ):
        """Move one exposure endpoint by an exact fixed increment."""
        if which == "black":
            var = self.black_var
            scale = self.black_scale
        elif which == "white":
            var = self.white_var
            scale = self.white_scale
        else:
            raise ValueError(which)

        low = float(scale.cget("from"))
        high = float(scale.cget("to"))
        current = float(var.get())
        value = min(
            high,
            max(low, current + float(delta)),
        )

        value = round(value, 4)

        self.loading_sliders = True
        try:
            var.set(value)
        finally:
            self.loading_sliders = False

        self._mark_current_exposure_override()
        self._finish_exposure_setup()
        self.refresh_preview(
            debounce=True
        )


    def on_slider(
        self,
        _value=None,
    ):
        if self.loading_sliders:
            return

        self._mark_current_exposure_override()
        self._finish_exposure_setup()
        self.refresh_preview(
            debounce=True
        )

    def unset_current_image_exposure(
        self,
    ):
        key = (
            int(
                self.current_file_index
            ),
            str(
                self.current_channel
            ),
        )

        self.image_exposure_overrides.pop(
            key,
            None,
        )
        self._finish_exposure_setup(clear_picks=True)
        self.exposure_pick_status_label.configure(
            text=(
                "Series average selected. Temporary exposure preview is off; "
                "the displayed image now uses the effective series average."
            )
        )
        self._load_effective_exposure_into_sliders()
        self.refresh_preview()

    def reset_current_exposure(
        self,
    ):
        baseline = self.channel_baseline[
            self.current_channel
        ]

        self.loading_sliders = True

        try:
            self.black_var.set(
                float(
                    baseline[
                        "black"
                    ]
                )
            )
            self.white_var.set(
                float(
                    baseline[
                        "white"
                    ]
                )
            )
        finally:
            self.loading_sliders = False

        self._mark_current_exposure_override()
        self._finish_exposure_setup()
        self.refresh_preview()

    # ------------------------------------------------------------------
    # Optional freehand counting ROI
    # ------------------------------------------------------------------

    def _current_custom_roi_key(self):
        return (
            int(self.current_file_index),
            str(self.current_channel),
            str(self.custom_roi_hemisphere_var.get()).upper(),
        )

    def _current_custom_roi_mode(self):
        return (
            "exclude"
            if bool(self.custom_roi_exclusion_var.get())
            else DEFAULT_CUSTOM_ROI_MODE
        )

    def _current_custom_roi_color(self):
        if self._current_custom_roi_mode() == "exclude":
            return CUSTOM_ROI_EXCLUSION_COLOR
        hemisphere = str(self.custom_roi_hemisphere_var.get()).upper()
        return CUSTOM_ROI_COLORS.get(hemisphere, CUSTOM_ROI_COLORS["L"])

    def _on_custom_roi_mode_changed(self):
        """Update feedback; existing ROIs retain their stored modes."""
        self._update_custom_roi_controls()
        if self.custom_roi_draw_active:
            self._draw_custom_roi_draft_overlay()

    def _cancel_custom_roi_draft(self, deactivate=False):
        self.custom_roi_draft_yx = []
        try:
            self.preview_canvas.delete(self.custom_roi_canvas_tag)
        except Exception:
            pass
        if deactivate:
            self.custom_roi_draw_active = False

    def _update_custom_roi_controls(self):
        if not hasattr(self, "custom_roi_draw_buttons"):
            return

        active_hemisphere = str(self.custom_roi_hemisphere_var.get()).upper()
        roi_status = {}
        for hemisphere in ("L", "R"):
            polygon = self.custom_counting_rois_yx.get((
                int(self.current_file_index),
                str(self.current_channel),
                hemisphere,
            ))
            has_roi = (
                polygon is not None
                and len(polygon) >= CUSTOM_ROI_MIN_VERTICES
            )
            roi_key = (
                int(self.current_file_index),
                str(self.current_channel),
                hemisphere,
            )
            saved_mode = str(self.custom_counting_roi_modes.get(
                roi_key,
                DEFAULT_CUSTOM_ROI_MODE,
            )).lower()
            if saved_mode not in CUSTOM_ROI_MODES:
                saved_mode = DEFAULT_CUSTOM_ROI_MODE
            roi_status[hemisphere] = (has_roi, polygon, saved_mode)

            is_drawing = (
                self.custom_roi_draw_active
                and hemisphere == active_hemisphere
            )
            self.custom_roi_draw_buttons[hemisphere].configure(
                text=(
                    f"Drawing {hemisphere}…"
                    if is_drawing
                    else f"Draw {hemisphere} ROI"
                ),
                style=("ActiveChannel.TButton" if is_drawing else "TButton"),
            )
            try:
                self.custom_roi_clear_buttons[hemisphere].state(
                    ["!disabled"] if has_roi else ["disabled"]
                )
            except Exception:
                pass

        if self.custom_roi_draw_active:
            color_cfg = CUSTOM_ROI_COLORS[active_hemisphere]
            drawing_mode = self._current_custom_roi_mode()
            color_cfg = (
                CUSTOM_ROI_EXCLUSION_COLOR
                if drawing_mode == "exclude"
                else color_cfg
            )
            self.custom_roi_status_label.configure(
                text=(
                    f"{drawing_mode.upper()}: drag around the "
                    f"{active_hemisphere} area for "
                    f"{self.current_channel}; "
                    + (
                        "cells inside will be ignored. "
                        if drawing_mode == "exclude"
                        else "only cells inside will be counted. "
                    )
                    + "Release to close it; click the active button to cancel."
                ),
                foreground=color_cfg["outline"],
            )
        else:
            parts = []
            for hemisphere in ("L", "R"):
                has_roi, polygon, saved_mode = roi_status[hemisphere]
                parts.append(
                    f"{hemisphere}: {saved_mode}, {len(polygon)} points"
                    if has_roi
                    else f"{hemisphere}: none"
                )
            self.custom_roi_status_label.configure(
                text=(
                    "  |  ".join(parts)
                ),
                foreground=GUI_MUTED_FG,
            )

    def start_custom_roi_draw(self, hemisphere):
        hemisphere = str(hemisphere).upper()
        if hemisphere not in ("L", "R"):
            raise ValueError(hemisphere)

        if (
            self.custom_roi_draw_active
            and str(self.custom_roi_hemisphere_var.get()).upper() == hemisphere
        ):
            self._cancel_custom_roi_draft(deactivate=True)
            self._update_custom_roi_controls()
            self._update_preview_cursor()
            return

        self._cancel_custom_roi_draft(deactivate=True)
        self.custom_roi_hemisphere_var.set(hemisphere)
        self._cancel_midline_drag()
        self.exposure_pick_mode = None
        self._update_exposure_pick_button_styles()
        self.landmark_sequence_active = False
        self.landmark_var.set("")
        self.current_landmark = None
        self._update_landmark_button_styles()
        self.custom_roi_draw_active = True
        self.custom_roi_draft_yx = []

        self._update_custom_roi_controls()
        self._update_preview_cursor()

    def clear_custom_roi(self, hemisphere):
        hemisphere = str(hemisphere).upper()
        if hemisphere not in ("L", "R"):
            raise ValueError(hemisphere)
        self._cancel_custom_roi_draft(deactivate=True)
        self.custom_counting_rois_yx.pop(
            (
                int(self.current_file_index),
                str(self.current_channel),
                hemisphere,
            ),
            None,
        )
        self.custom_counting_roi_modes.pop(
            (
                int(self.current_file_index),
                str(self.current_channel),
                hemisphere,
            ),
            None,
        )
        self._update_custom_roi_controls()
        self._update_preview_cursor()
        self.refresh_preview()

    def _draw_custom_roi_draft_overlay(self):
        self.preview_canvas.delete(self.custom_roi_canvas_tag)
        if len(self.custom_roi_draft_yx) < 2:
            return

        canvas_xy = []
        for y, x in self.custom_roi_draft_yx:
            canvas_xy.extend([
                float(self.preview_offset_x) + float(x) * self.preview_scale,
                float(self.preview_offset_y) + float(y) * self.preview_scale,
            ])
        self.preview_canvas.create_line(
            *canvas_xy,
            fill=self._current_custom_roi_color()["outline"],
            width=3,
            tags=(self.custom_roi_canvas_tag,),
        )

    def _placement_tool_active(self):
        return (
            self.custom_roi_draw_active
            or self.exposure_pick_mode is not None
            or self.current_landmark in MANUAL_GUI_LANDMARKS
        )

    def _create_native_placement_cursor(self):
        """Create a native white cross cursor; Windows moves it independently.

        The previous white cross consisted of Canvas line objects updated for
        every mouse-motion event. Preview repaints could therefore make it lag
        behind or flicker. Tk can load a Windows ``.cur`` file directly, so a
        tiny cursor is generated once in the user's temporary directory and is
        thereafter rendered by the operating system.
        """
        try:
            import io
            import struct
            import tempfile

            size = 32
            centre = 15
            cursor_image = self.Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = self.ImageDraw.Draw(cursor_image)

            # A narrow dark edge keeps the white cross visible over bright
            # cells without changing its familiar, simple cross shape.
            for width, colour in (
                (3, (0, 0, 0, 255)),
                (1, (255, 255, 255, 255)),
            ):
                draw.line((centre, 3, centre, 28), fill=colour, width=width)
                draw.line((3, centre, 28, centre), fill=colour, width=width)

            png_buffer = io.BytesIO()
            cursor_image.save(png_buffer, format="PNG")
            png_bytes = png_buffer.getvalue()

            # CUR header + one directory entry + a PNG image. The hotspot is
            # the exact intersection of the two lines.
            cursor_bytes = (
                struct.pack("<HHH", 0, 2, 1)
                + struct.pack(
                    "<BBBBHHII",
                    size,
                    size,
                    0,
                    0,
                    centre,
                    centre,
                    len(png_bytes),
                    22,
                )
                + png_bytes
            )
            cursor_path = Path(tempfile.gettempdir()) / "neurodot_white_cross.cur"
            if not cursor_path.exists() or cursor_path.read_bytes() != cursor_bytes:
                cursor_path.write_bytes(cursor_bytes)

            cursor_spec = "@" + cursor_path.as_posix()
            # Ask Tk to load it now so any unsupported platform/file error is
            # caught here, rather than later during an interaction.
            self.root.configure(cursor=cursor_spec)
            self.root.configure(cursor="")
            return cursor_spec
        except Exception:
            # Still use a native cursor on unusual Tk/platform builds. It may
            # not be white there, but it remains responsive and flicker-free.
            return "crosshair"

    def _update_preview_cursor(self):
        """Select native cursors only; no mouse-following Canvas graphics."""
        if not hasattr(self, "preview_canvas"):
            return
        cursor = "pencil" if self.custom_roi_draw_active else (
            self.placement_cursor if self._placement_tool_active() else "arrow"
        )
        try:
            self.preview_canvas.configure(cursor=cursor)
        except Exception:
            self.preview_canvas.configure(cursor="crosshair")

    # ------------------------------------------------------------------
    # Preview zoom / pan
    # ------------------------------------------------------------------

    def _reset_preview_view(self, refresh=True):
        self.preview_zoom = 1.0
        self.preview_pan_x = 0.0
        self.preview_pan_y = 0.0
        self.preview_pan_active = False
        self.preview_pan_last_xy = None

        if refresh:
            if self.preview_native_pil is not None:
                self._render_cached_preview_to_canvas()
            else:
                self.refresh_preview()


    def on_preview_zoom_reset(self, event=None):
        self._reset_preview_view(refresh=True)
        return "break"


    def on_preview_mousewheel(self, event):
        """Zoom around the cursor using the already-composited RAM cache."""
        if self.preview_native_pil is None or self.preview_scale <= 0:
            return "break"

        delta = int(getattr(event, "delta", 0) or 0)
        if delta > 0 or getattr(event, "num", None) == 4:
            factor = float(GUI_PREVIEW_ZOOM_STEP)
        elif delta < 0 or getattr(event, "num", None) == 5:
            factor = 1.0 / float(GUI_PREVIEW_ZOOM_STEP)
        else:
            return "break"

        old_zoom = float(self.preview_zoom)
        new_zoom = float(np.clip(
            old_zoom * factor,
            float(GUI_PREVIEW_ZOOM_MIN),
            float(GUI_PREVIEW_ZOOM_MAX),
        ))

        if abs(new_zoom - old_zoom) < 1e-12:
            return "break"

        native_x = (
            float(event.x) - float(self.preview_offset_x)
        ) / float(self.preview_scale)
        native_y = (
            float(event.y) - float(self.preview_offset_y)
        ) / float(self.preview_scale)

        self.preview_zoom = new_zoom

        native_w, native_h = self.preview_native_pil.size
        canvas_w = max(1, int(self.preview_canvas.winfo_width()))
        canvas_h = max(1, int(self.preview_canvas.winfo_height()))

        new_scale = self._calculate_preview_scale(
            native_w,
            native_h,
        )
        display_w = native_w * new_scale
        display_h = native_h * new_scale
        centered_x = (canvas_w - display_w) / 2.0
        centered_y = (canvas_h - display_h) / 2.0

        desired_x = float(event.x) - native_x * new_scale
        desired_y = float(event.y) - native_y * new_scale

        self.preview_pan_x = desired_x - centered_x
        self.preview_pan_y = desired_y - centered_y

        if new_zoom <= 1.0 + 1e-9:
            self.preview_zoom = 1.0
            self.preview_pan_x = 0.0
            self.preview_pan_y = 0.0

        self._render_cached_preview_to_canvas()
        return "break"


    def on_preview_pan_press(self, event):
        if self.preview_zoom <= 1.0 + 1e-9:
            return "break"

        self.preview_pan_active = True
        self.preview_pan_last_xy = (
            float(event.x),
            float(event.y),
        )
        try:
            self.preview_canvas.configure(cursor="fleur")
        except Exception:
            pass
        return "break"


    def on_preview_pan_drag(self, event):
        """Pan by moving the existing Canvas item; no image resampling."""
        if not self.preview_pan_active or self.preview_pan_last_xy is None:
            return "break"

        x0, y0 = self.preview_pan_last_xy
        x1, y1 = float(event.x), float(event.y)
        dx = x1 - x0
        dy = y1 - y0

        self.preview_pan_x += dx
        self.preview_pan_y += dy
        self.preview_offset_x += dx
        self.preview_offset_y += dy
        self.preview_pan_last_xy = (x1, y1)

        if self.preview_image_item is not None:
            try:
                self.preview_canvas.coords(
                    self.preview_image_item,
                    self.preview_offset_x,
                    self.preview_offset_y,
                )
            except Exception:
                pass

        return "break"


    def on_preview_pan_release(self, event=None):
        self.preview_pan_active = False
        self.preview_pan_last_xy = None
        self._update_preview_cursor()
        return "break"


    # ------------------------------------------------------------------
    # Landmark placement
    # ------------------------------------------------------------------

    def _update_landmark_button_styles(self):
        """Green-outline only the landmark currently waiting for placement."""
        if not hasattr(self, "landmark_buttons"):
            return
        selected = str(self.landmark_var.get())
        for key, button in self.landmark_buttons.items():
            active = key == selected and self.current_landmark == key
            self.landmark_borders[key].configure(
                background=(GUI_ACCENT if active else GUI_BORDER)
            )
            button.configure(
                background=GUI_CONTROL_BG,
                activebackground=GUI_CONTROL_ACTIVE_BG,
            )

    def _select_landmark(self, landmark):
        """Activate one explicit, one-shot landmark replacement."""
        if landmark not in MANUAL_GUI_LANDMARKS:
            return
        self._cancel_custom_roi_draft(deactivate=True)
        self._cancel_midline_drag()
        self.exposure_pick_mode = None
        self._update_exposure_pick_button_styles()
        self.landmark_sequence_active = False
        self.landmark_var.set(landmark)
        self.current_landmark = landmark
        self._update_landmark_button_styles()
        self._update_preview_cursor()
        self.exposure_pick_status_label.configure(
            text=(
                f"LANDMARK ACTIVE: {MANUAL_GUI_LANDMARKS[landmark]['label']}. "
                "Click once in the image to place or replace it."
            )
        )
        self.refresh_preview()

    def on_landmark_mode_changed(
        self,
    ):
        self._select_landmark(str(self.landmark_var.get()))

    def on_preview_canvas_resize(
        self,
        event=None,
    ):
        # Resize the already-composited preview instead of rebuilding exposure
        # and overlays during Windows geometry/configure events.
        try:
            if self.preview_native_pil is not None:
                self.root.after_idle(
                    self._render_cached_preview_to_canvas
                )
            else:
                self.root.after_idle(
                    self.refresh_preview
                )
        except Exception:
            pass

    def _canvas_event_to_native_yx(self, event):
        """Convert a Canvas mouse event to logical image (y, x), or None."""
        if self.preview_scale <= 0:
            return None

        display_w, display_h = self.preview_display_size
        local_x = float(event.x) - float(self.preview_offset_x)
        local_y = float(event.y) - float(self.preview_offset_y)

        if (
            local_x < 0
            or local_y < 0
            or local_x >= display_w
            or local_y >= display_h
        ):
            return None

        native_h, native_w = self.preview_native_shape
        x = np.clip(
            local_x / self.preview_scale,
            0.0,
            max(0.0, native_w - 1.0),
        )
        y = np.clip(
            local_y / self.preview_scale,
            0.0,
            max(0.0, native_h - 1.0),
        )
        return float(y), float(x)

    def _commit_landmark_yx(self, landmark, y, x):
        """Store one landmark and apply the normal automatic-advance logic."""
        points = self.manual_landmarks_yx[self.current_file_index]
        points[landmark] = [float(y), float(x)]

        ordered = list(MANUAL_GUI_LANDMARKS.keys())
        idx = ordered.index(landmark)

        if landmark == "rot_top" and "rot_bottom" in points:
            y_bottom, x_bottom = map(float, points["rot_bottom"])
            y_top, x_top = map(float, points["rot_top"])
            points["ce"] = [
                (y_bottom + y_top) / 2.0,
                (x_bottom + x_top) / 2.0,
            ]

        if not self.landmark_sequence_active:
            self.landmark_var.set("")
            self.current_landmark = None
            self._update_landmark_button_styles()
            self._update_preview_cursor()
            return

        next_landmark = next(
            (key for key in ordered[idx + 1:] if key not in points),
            None,
        )
        if next_landmark is not None:
            self.landmark_var.set(next_landmark)
            self.current_landmark = next_landmark
            self._update_landmark_button_styles()
            self._update_preview_cursor()
        else:
            # The landmark workflow flows directly into exposure calibration:
            # final bilateral landmark -> weakest positive -> brightest background.
            self.landmark_sequence_active = False
            self.landmark_var.set("")
            self.current_landmark = None
            self._update_landmark_button_styles()
            self._set_exposure_pick_mode("positive")

    def _cancel_midline_drag(self):
        self.midline_drag_active = False
        try:
            self.preview_canvas.delete(self.midline_drag_tag)
        except Exception:
            pass

    def _draw_midline_drag_overlay(self, event):
        """Move only a cheap Canvas line/endpoint overlay while dragging."""
        points = self.manual_landmarks_yx[self.current_file_index]
        if "rot_bottom" not in points:
            return

        yx = self._canvas_event_to_native_yx(event)
        if yx is None:
            return

        y_bottom, x_bottom = points["rot_bottom"]
        y_top, x_top = yx

        x1 = float(self.preview_offset_x) + float(x_bottom) * self.preview_scale
        y1 = float(self.preview_offset_y) + float(y_bottom) * self.preview_scale
        x2 = float(self.preview_offset_x) + float(x_top) * self.preview_scale
        y2 = float(self.preview_offset_y) + float(y_top) * self.preview_scale

        self.preview_canvas.delete(self.midline_drag_tag)
        self.preview_canvas.create_line(
            x1, y1, x2, y2,
            fill="#ffffff",
            width=3,
            tags=(self.midline_drag_tag,),
        )
        radius = 6
        self.preview_canvas.create_oval(
            x2 - radius,
            y2 - radius,
            x2 + radius,
            y2 + radius,
            outline="#ff4444",
            width=2,
            tags=(self.midline_drag_tag,),
        )

    def on_preview_button_press(self, event):
        if self.custom_roi_draw_active:
            yx = self._canvas_event_to_native_yx(event)
            if yx is None:
                return
            self.custom_roi_draft_yx = [[float(yx[0]), float(yx[1])]]
            self.preview_canvas.delete(self.custom_roi_canvas_tag)
            return

        if self._apply_exposure_calibration_pick(event):
            return

        landmark = str(self.landmark_var.get())
        if landmark not in MANUAL_GUI_LANDMARKS:
            return

        # The second midline point is a click-drag-release interaction.  The
        # previously placed anatomical bottom point is the fixed end of the line.
        if (
            landmark == "rot_top"
            and "rot_bottom" in self.manual_landmarks_yx[self.current_file_index]
        ):
            if self._canvas_event_to_native_yx(event) is None:
                return
            self.midline_drag_active = True
            self._draw_midline_drag_overlay(event)
            return

        # All other landmarks retain the original single-click behaviour.
        yx = self._canvas_event_to_native_yx(event)
        if yx is None:
            return
        y, x = yx
        self._commit_landmark_yx(landmark, y, x)
        self.refresh_preview()

    def on_preview_drag(self, event):
        if self.custom_roi_draw_active and self.custom_roi_draft_yx:
            yx = self._canvas_event_to_native_yx(event)
            if yx is None:
                return
            y, x = map(float, yx)
            last_y, last_x = self.custom_roi_draft_yx[-1]
            if math.hypot(x - last_x, y - last_y) >= float(
                CUSTOM_ROI_MIN_SAMPLE_DISTANCE_PX
            ):
                self.custom_roi_draft_yx.append([y, x])
                self._draw_custom_roi_draft_overlay()
            return

        if not self.midline_drag_active:
            return
        self._draw_midline_drag_overlay(event)

    def on_preview_button_release(self, event):
        if self.custom_roi_draw_active:
            completed_hemisphere = str(
                self.custom_roi_hemisphere_var.get()
            ).upper()
            yx = self._canvas_event_to_native_yx(event)
            if yx is not None and self.custom_roi_draft_yx:
                y, x = map(float, yx)
                last_y, last_x = self.custom_roi_draft_yx[-1]
                if math.hypot(x - last_x, y - last_y) > 0.0:
                    self.custom_roi_draft_yx.append([y, x])

            completed_valid_roi = (
                len(self.custom_roi_draft_yx) >= CUSTOM_ROI_MIN_VERTICES
            )
            if completed_valid_roi:
                completed_key = self._current_custom_roi_key()
                self.custom_counting_rois_yx[completed_key] = [
                    [float(y), float(x)]
                    for y, x in self.custom_roi_draft_yx
                ]
                self.custom_counting_roi_modes[
                    completed_key
                ] = self._current_custom_roi_mode()

            self._cancel_custom_roi_draft(deactivate=True)

            # The normal bilateral workflow is L followed immediately by R.
            # An invalid short stroke remains on the same side for retry.
            if completed_valid_roi and completed_hemisphere == "L":
                self.custom_roi_hemisphere_var.set("R")
                self.custom_roi_draw_active = True
            elif not completed_valid_roi:
                self.custom_roi_hemisphere_var.set(completed_hemisphere)
                self.custom_roi_draw_active = True

            self._update_custom_roi_controls()
            self._update_preview_cursor()
            self.refresh_preview()
            return

        if not self.midline_drag_active:
            return

        yx = self._canvas_event_to_native_yx(event)
        self.midline_drag_active = False
        self.preview_canvas.delete(self.midline_drag_tag)

        if yx is None:
            # Releasing outside the image cancels the placement rather than
            # creating a clipped or accidental top point.
            return

        y, x = yx
        self._commit_landmark_yx("rot_top", y, x)
        self.refresh_preview()

    def clear_selected_landmark(
        self,
    ):
        landmark = str(
            self.landmark_var.get()
        )

        self.manual_landmarks_yx[
            self.current_file_index
        ].pop(
            landmark,
            None,
        )

        self.refresh_preview()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _calculate_preview_scale(self, native_w, native_h):
        self.preview_canvas.update_idletasks()

        available_w = max(
            500,
            int(self.preview_canvas.winfo_width()),
        )
        available_h = max(
            400,
            int(self.preview_canvas.winfo_height()),
        )

        fit_scale = min(
            EXPOSURE_PREVIEW_MAX_WIDTH / max(native_w, 1),
            EXPOSURE_PREVIEW_MAX_HEIGHT / max(native_h, 1),
            available_w / max(native_w, 1),
            available_h / max(native_h, 1),
        )
        fit_scale = max(1e-6, float(fit_scale))
        self.preview_fit_scale = fit_scale

        return max(
            1e-6,
            fit_scale * float(self.preview_zoom),
        )


    def _render_cached_preview_to_canvas(self):
        """Resize only the RAM-cached composite and show it on the Canvas."""
        if self.preview_native_pil is None:
            return

        native_w, native_h = self.preview_native_pil.size
        scale = self._calculate_preview_scale(
            native_w,
            native_h,
        )

        display_w = max(1, int(round(native_w * scale)))
        display_h = max(1, int(round(native_h * scale)))

        self.preview_scale = float(scale)
        self.preview_display_size = (
            display_w,
            display_h,
        )
        self.preview_native_shape = (
            native_h,
            native_w,
        )

        resized = self.preview_native_pil.resize(
            (display_w, display_h),
            resample=self.Image.Resampling.LANCZOS,
        )
        self.photo = self.ImageTk.PhotoImage(resized, master=self.root)

        self.preview_canvas.delete("all")
        self.preview_canvas.update_idletasks()

        canvas_w = max(1, int(self.preview_canvas.winfo_width()))
        canvas_h = max(1, int(self.preview_canvas.winfo_height()))

        centered_x = (canvas_w - display_w) / 2.0
        centered_y = (canvas_h - display_h) / 2.0
        self.preview_offset_x = centered_x + float(self.preview_pan_x)
        self.preview_offset_y = centered_y + float(self.preview_pan_y)

        self.preview_image_item = self.preview_canvas.create_image(
            self.preview_offset_x,
            self.preview_offset_y,
            anchor="nw",
            image=self.photo,
        )

        self.preview_canvas.configure(
            scrollregion=(0, 0, canvas_w, canvas_h)
        )


    def _landmark_label_font(self, native_h, native_w):
        size = int(round(
            min(float(native_h), float(native_w))
            * float(LANDMARK_LABEL_FONT_FRACTION)
        ))
        size = int(np.clip(
            size,
            int(LANDMARK_LABEL_FONT_MIN_PX),
            int(LANDMARK_LABEL_FONT_MAX_PX),
        ))

        for font_name in ("arialbd.ttf", "DejaVuSans-Bold.ttf"):
            try:
                return self.ImageFont.truetype(font_name, size=size)
            except Exception:
                continue
        return self.ImageFont.load_default()

    def _draw_readable_landmark_label(
        self,
        pil,
        draw,
        px,
        py,
        text,
        color,
        font,
        point_radius,
    ):
        """Draw a compact edge-aware label beside a landmark dot."""
        gap = int(LANDMARK_LABEL_GAP_PX)
        try:
            bbox = draw.textbbox(
                (0, 0),
                text,
                font=font,
                stroke_width=1,
            )
        except Exception:
            bbox = (0, 0, max(8, len(text) * 8), 12)

        text_w = int(max(1, bbox[2] - bbox[0]))
        text_h = int(max(1, bbox[3] - bbox[1]))
        image_w, image_h = pil.size

        text_x = float(px) + float(point_radius) + gap
        if text_x + text_w > image_w - 2:
            text_x = float(px) - float(point_radius) - gap - text_w
        text_y = float(py) - text_h / 2.0
        text_x = float(np.clip(text_x, 2.0, max(2.0, image_w - text_w - 2.0)))
        text_y = float(np.clip(text_y, 2.0, max(2.0, image_h - text_h - 2.0)))

        draw.text(
            (
                text_x - bbox[0],
                text_y - bbox[1],
            ),
            text,
            fill=color,
            font=font,
            stroke_width=2,
            stroke_fill="#000000",
        )

    def _preview_rgb(
        self,
        windowed,
        masks=None,
        centers=None,
    ):
        """Build a native-resolution composited preview and cache it in RAM."""
        image = np.clip(
            np.asarray(windowed, dtype=np.float32),
            0.0,
            1.0,
        )

        u8 = (image * 255.0).astype(np.uint8)
        pil = self.Image.fromarray(
            u8,
            mode="L",
        ).convert("RGB")

        h, w = image.shape
        landmark_label_font = self._landmark_label_font(h, w)

        if masks is not None:
            masks = np.asarray(masks)
            edges = (
                masks
                != ndi.grey_erosion(
                    masks,
                    size=(3, 3),
                    mode="nearest",
                )
            )
            arr = np.asarray(pil).copy()
            arr[edges, 0] = 255
            arr[edges, 1] = 0
            arr[edges, 2] = 255
            pil = self.Image.fromarray(arr)

        draw = self.ImageDraw.Draw(pil)

        if centers is not None and len(centers):
            for cy, cx in centers:
                px = float(cx)
                py = float(cy)
                radius = 3
                draw.ellipse(
                    [
                        px - radius,
                        py - radius,
                        px + radius,
                        py + radius,
                    ],
                    outline=(255, 255, 0),
                    width=1,
                )

        points = self.manual_landmarks_yx[
            self.current_file_index
        ]

        if all(key in points for key in ROTATION_LANDMARK_KEYS):
            y1, x1 = points[ROTATION_LANDMARK_KEYS[0]]
            y2, x2 = points[ROTATION_LANDMARK_KEYS[1]]
            draw.line(
                [
                    float(x1),
                    float(y1),
                    float(x2),
                    float(y2),
                ],
                fill="#ffffff",
                width=2,
            )

        def draw_dashed_segment(p0, p1):
            x0, y0 = map(float, p0)
            x1, y1 = map(float, p1)
            dx = x1 - x0
            dy = y1 - y0
            length = math.hypot(dx, dy)
            if length <= 1e-9:
                return

            ux, uy = dx / length, dy / length
            dash = max(2.0, float(COUNTING_ROI_DASH_PX))
            gap = max(1.0, float(COUNTING_ROI_GAP_PX))
            pos = 0.0

            while pos < length:
                segment_end = min(length, pos + dash)
                draw.line(
                    [
                        x0 + ux * pos,
                        y0 + uy * pos,
                        x0 + ux * segment_end,
                        y0 + uy * segment_end,
                    ],
                    fill=COUNTING_ROI_GUI_COLOR,
                    width=1,
                )
                pos += dash + gap

        if all(key in points for key in MANUAL_GUI_LANDMARKS):
            for hemi in ("L", "R"):
                corners = build_counting_rectangle_yx(
                    points,
                    hemi,
                    margin_px=COUNTING_ROI_MARGIN_PX,
                )
                if corners is None:
                    continue

                display_xy = [
                    (float(x), float(y))
                    for y, x in corners
                ]
                for i in range(4):
                    draw_dashed_segment(
                        display_xy[i],
                        display_xy[(i + 1) % 4],
                    )

                counting_region = str(
                    self.counting_region_var.get()
                ).strip().lower()
                if counting_region in ("dorsal", "ventral"):
                    selected_polygon = build_selected_counting_region_polygon_yx(
                        points,
                        hemi,
                        counting_region,
                        margin_px=COUNTING_ROI_MARGIN_PX,
                    )
                    if selected_polygon is not None:
                        selected_xy = [
                            (float(x), float(y))
                            for y, x in selected_polygon
                        ]
                        # Keep the fluorescence unobscured: a solid perimeter
                        # marks the selected half, while the complete rectangle
                        # remains visible as a dashed outline.
                        draw.line(
                            selected_xy + [selected_xy[0]],
                            fill=GUI_ACCENT,
                            width=3,
                        )

                        outer_indices = (
                            (2, 3)
                            if counting_region == "dorsal"
                            else (0, 1)
                        )
                        outer_x = sum(
                            selected_xy[i][0] for i in outer_indices
                        ) / 2.0
                        outer_y = sum(
                            selected_xy[i][1] for i in outer_indices
                        ) / 2.0
                        centre_x = sum(x for x, _ in selected_xy) / len(selected_xy)
                        centre_y = sum(y for _, y in selected_xy) / len(selected_xy)
                        label_x = 0.85 * outer_x + 0.15 * centre_x
                        label_y = 0.85 * outer_y + 0.15 * centre_y
                        draw.text(
                            (label_x, label_y),
                            counting_region.upper(),
                            fill=GUI_ACCENT,
                            anchor="mm",
                            font=landmark_label_font,
                            stroke_width=2,
                            stroke_fill="#000000",
                        )

                    divider = build_counting_region_divider_yx(
                        points,
                        hemi,
                        margin_px=COUNTING_ROI_MARGIN_PX,
                    )
                    if divider is not None:
                        draw.line(
                            [
                                (float(divider[0, 1]), float(divider[0, 0])),
                                (float(divider[1, 1]), float(divider[1, 0])),
                            ],
                            fill=COUNTING_DIVIDER_GUI_COLOR,
                            width=2,
                        )

        for hemisphere in ("L", "R"):
            roi_key = (
                int(self.current_file_index),
                str(self.current_channel),
                hemisphere,
            )
            custom_polygon = self.custom_counting_rois_yx.get(roi_key)
            if (
                custom_polygon is None
                or len(custom_polygon) < CUSTOM_ROI_MIN_VERTICES
            ):
                continue

            roi_mode = str(self.custom_counting_roi_modes.get(
                roi_key,
                DEFAULT_CUSTOM_ROI_MODE,
            )).strip().lower()
            if roi_mode not in CUSTOM_ROI_MODES:
                roi_mode = DEFAULT_CUSTOM_ROI_MODE
            color_cfg = (
                CUSTOM_ROI_EXCLUSION_COLOR
                if roi_mode == "exclude"
                else CUSTOM_ROI_COLORS[hemisphere]
            )
            custom_xy = [
                (float(x), float(y))
                for y, x in custom_polygon
            ]
            custom_draw = self.ImageDraw.Draw(pil, "RGBA")
            custom_draw.polygon(
                custom_xy,
                fill=color_cfg["fill"],
                outline=color_cfg["outline"],
                width=3,
            )
            label_x = sum(x for x, _ in custom_xy) / len(custom_xy)
            label_y = sum(y for _, y in custom_xy) / len(custom_xy)
            draw.text(
                (label_x, label_y),
                f"{hemisphere} {roi_mode.upper()} ROI",
                fill=color_cfg["outline"],
                anchor="mm",
            )

        calibration_key = (
            int(self.current_file_index),
            str(self.current_channel),
        )
        calibration_picks = self.exposure_calibration_picks.get(
            calibration_key,
            {},
        )

        for pick_name, color in (
            ("background", EXPOSURE_PICK_BACKGROUND_COLOR),
            ("positive", EXPOSURE_PICK_POSITIVE_COLOR),
        ):
            pick = calibration_picks.get(pick_name)
            if pick is None:
                continue

            cx = float(pick["center_x"])
            cy = float(pick["center_y"])
            radius = float(pick["radius_px"])
            bx = float(pick["bright_x"])
            by = float(pick["bright_y"])

            draw.ellipse(
                [
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                ],
                outline=color,
                width=2,
            )

            cross = 5
            draw.line(
                [bx - cross, by, bx + cross, by],
                fill=color,
                width=2,
            )
            draw.line(
                [bx, by - cross, bx, by + cross],
                fill=color,
                width=2,
            )

            short_label = "BG" if pick_name == "background" else "POS"
            draw.text(
                (cx + radius + 4, cy - 8),
                f"{short_label} {pick['value']:.1f}",
                fill=color,
            )

        for key, yx in points.items():
            if key not in MANUAL_GUI_LANDMARKS:
                continue

            cy, cx = yx
            px = float(cx)
            py = float(cy)
            color = MANUAL_GUI_LANDMARKS[key]["color"]
            radius = 6

            draw.ellipse(
                [
                    px - radius,
                    py - radius,
                    px + radius,
                    py + radius,
                ],
                fill=color,
                outline="white",
                width=1,
            )
            self._draw_readable_landmark_label(
                pil=pil,
                draw=draw,
                px=px,
                py=py,
                text=MANUAL_GUI_LANDMARKS[key]["label"],
                color=color,
                font=landmark_label_font,
                point_radius=radius,
            )

        self.preview_native_pil = pil
        self.preview_native_shape = (h, w)
        return pil


    def _draw_histogram(
        self,
        mip,
        black,
        white,
    ):
        canvas = self.hist_canvas
        canvas.delete(
            "all"
        )
        canvas.update_idletasks()

        width = max(
            10,
            canvas.winfo_width(),
        )

        height = max(
            10,
            canvas.winfo_height(),
        )

        if mip is None:
            return

        values = np.asarray(
            mip,
            dtype=np.float32,
        ).ravel()

        values = values[
            np.isfinite(
                values
            )
        ]

        if (
            values.size
            > EXPOSURE_HISTOGRAM_SAMPLE_PIXELS
        ):
            step = max(
                1,
                values.size
                // EXPOSURE_HISTOGRAM_SAMPLE_PIXELS,
            )

            values = values[
                ::step
            ][
                :EXPOSURE_HISTOGRAM_SAMPLE_PIXELS
            ]

        if values.size == 0:
            return

        baseline = self.channel_baseline[
            self.current_channel
        ]

        upper = max(
            float(
                np.max(
                    values
                )
            ),
            float(
                baseline[
                    "slider_max"
                ]
            ),
            1.0,
        )

        hist, _ = np.histogram(
            values,
            bins=EXPOSURE_HISTOGRAM_BINS,
            range=(
                0.0,
                upper,
            ),
        )

        y = np.log1p(
            hist.astype(
                np.float64
            )
        )

        if np.max(
            y
        ) > 0:
            y /= np.max(
                y
            )

        points = []

        for i, value in enumerate(
            y
        ):
            x = (
                i
                / max(
                    1,
                    len(
                        y
                    )
                    - 1,
                )
                * (
                    width - 1
                )
            )

            yy = (
                height - 1
            ) - value * (
                height - 12
            )

            points.extend(
                [
                    x,
                    yy,
                ]
            )

        if len(
            points
        ) >= 4:
            canvas.create_line(
                *points,
                fill="#dddddd",
                width=1,
            )

        for value, color, label in (
            (
                black,
                "#00ff00",
                "B",
            ),
            (
                white,
                "#ff4444",
                "W",
            ),
        ):
            x = (
                np.clip(
                    value / upper,
                    0.0,
                    1.0,
                )
                * (
                    width - 1
                )
            )

            canvas.create_line(
                x,
                0,
                x,
                height,
                fill=color,
                width=2,
            )

            canvas.create_text(
                x + 8,
                10,
                text=label,
                fill=color,
            )

    def _cellpose_preview_keep_mask(self, centers, channel=None):
        """Apply the production counting geometry to preview centroids.

        Production first assigns each spot to L/R using the directed midline,
        then intersects that side with its landmark rectangle, the channel's
        whole/dorsal/ventral choice, and its optional custom ROI. Keeping this
        calculation in native image coordinates makes the preview agree with
        the eventual exported counts without rerunning Cellpose.
        """
        centers = np.asarray(centers, dtype=np.float64)
        if centers.size == 0:
            return np.zeros((0,), dtype=bool)
        centers = centers.reshape((-1, 2))

        channel = str(channel or self.current_channel)
        points = self.manual_landmarks_yx.get(
            int(self.current_file_index),
            {},
        )
        if not all(key in points for key in ROTATION_LANDMARK_KEYS):
            return np.ones(len(centers), dtype=bool)

        y_bottom, x_bottom = map(float, points["rot_bottom"])
        y_top, x_top = map(float, points["rot_top"])
        dx = x_top - x_bottom
        dy = y_top - y_bottom
        if abs(dx) < 1e-12 and abs(dy) < 1e-12:
            return np.ones(len(centers), dtype=bool)

        py = centers[:, 0]
        px = centers[:, 1]
        cross = dx * (py - y_bottom) - dy * (px - x_bottom)
        eps = 1e-6
        side_membership = {
            "L": cross <= eps,
            "R": cross >= -eps,
        }

        region = str(self.channel_counting_regions.get(
            channel,
            DEFAULT_COUNTING_REGION,
        )).strip().lower()
        if region not in COUNTING_REGION_MODES:
            region = DEFAULT_COUNTING_REGION

        retained = np.zeros(len(centers), dtype=bool)
        for hemisphere in ("L", "R"):
            keep = counting_rectangle_mask_yx(
                centers,
                points,
                hemisphere,
                counting_region=region,
            )

            roi_key = (
                int(self.current_file_index),
                channel,
                hemisphere,
            )
            polygon = self.custom_counting_rois_yx.get(roi_key)
            if polygon is not None and len(polygon) >= CUSTOM_ROI_MIN_VERTICES:
                roi_mode = str(self.custom_counting_roi_modes.get(
                    roi_key,
                    DEFAULT_CUSTOM_ROI_MODE,
                )).strip().lower()
                if roi_mode not in CUSTOM_ROI_MODES:
                    roi_mode = DEFAULT_CUSTOM_ROI_MODE
                inside_roi = points_in_polygon_yx(centers, polygon)
                if roi_mode == "exclude":
                    keep &= ~inside_roi
                else:
                    keep &= inside_roi

            retained |= side_membership[hemisphere] & keep

        return retained

    def _filtered_cellpose_preview(self, cached_test, channel=None):
        """Return only Cellpose objects that would survive final filtering."""
        centers = np.asarray(
            cached_test.get("centers", np.empty((0, 2))),
            dtype=np.float32,
        ).reshape((-1, 2))
        keep = self._cellpose_preview_keep_mask(centers, channel=channel)
        filtered_centers = centers[keep]

        masks = cached_test.get("masks")
        accepted_labels = np.asarray(
            cached_test.get("accepted_labels", np.empty((0,))),
            dtype=np.int32,
        )
        filtered_masks = None
        if masks is not None and len(accepted_labels) == len(centers):
            masks = np.asarray(masks)
            kept_labels = accepted_labels[keep]
            if len(kept_labels):
                filtered_masks = np.where(
                    np.isin(masks, kept_labels),
                    masks,
                    0,
                ).astype(masks.dtype, copy=False)
            else:
                filtered_masks = np.zeros_like(masks)

        return filtered_masks, filtered_centers, int(np.count_nonzero(keep)), len(keep)

    def refresh_preview(
        self,
        debounce=False,
    ):
        if debounce:
            if self.preview_after_id is not None:
                try:
                    self.root.after_cancel(self.preview_after_id)
                except Exception:
                    pass
            self.preview_after_id = self.root.after(
                int(GUI_PREVIEW_DEBOUNCE_MS),
                lambda: self.refresh_preview(debounce=False),
            )
            return

        self.preview_after_id = None
        ims_path = self.ims_files[
            self.current_file_index
        ]

        channel = self.current_channel

        enabled_preview_channels = self._enabled_preview_channels()
        if channel not in enabled_preview_channels:
            if enabled_preview_channels:
                self.set_channel(enabled_preview_channels[0])
                return

            self.file_label.configure(
                text=(
                    f"Image {self.current_file_index + 1}/"
                    f"{len(self.ims_files)}: {ims_path.name}"
                )
            )
            self.image_completion_label.configure(text="No preview channel")
            self.exposure_mode_label.configure(
                text="All Count channels are disabled. Enable one to preview it."
            )
            self.numeric_label.configure(text="")
            self.preview_native_pil = None
            self.preview_image_item = None
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                20,
                20,
                anchor="nw",
                fill=GUI_MUTED_FG,
                text=(
                    "No channels are enabled for counting.\n"
                    "Enable a Count channel to restore its preview."
                ),
            )
            self.hist_canvas.delete("all")
            return

        mip = self._get_mip(
            self.current_file_index,
            channel,
        )

        self.file_label.configure(
            text=(
                f"Image {self.current_file_index + 1}/"
                f"{len(self.ims_files)}: {ims_path.name}"
            )
        )

        complete_count = sum(
            1
            for key in MANUAL_GUI_LANDMARKS
            if key
            in self.manual_landmarks_yx[
                self.current_file_index
            ]
        )

        self.image_completion_label.configure(
            text=(
                f"Landmarks {complete_count}/"
                f"{len(MANUAL_GUI_LANDMARKS)}"
            )
        )

        if mip is _MIP_LOADING:
            self.preview_native_pil = None
            self.preview_image_item = None
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                20,
                20,
                anchor="nw",
                fill="white",
                text=(
                    f"Loading {ims_path.name} / {channel} in background...\n"
                    "The GUI remains responsive while the full-resolution MIP is built."
                ),
            )
            return

        effective = self._effective_exposure(
            self.current_file_index,
            channel,
        )

        (
            black,
            white,
            using_forced_black_preview,
            slider_black,
            slider_white,
        ) = self._preview_black_white(mip)

        if effective[
            "source"
        ] == "individual":
            mode_text = (
                "INDIVIDUAL exposure for this image"
            )
        else:
            avg = self._series_average(
                channel
            )
            n_set = sum(
                1
                for (
                    _i,
                    ch
                ) in self.image_exposure_overrides
                if ch == channel
            )
            mode_text = (
                "UNSET → series average "
                f"({n_set} explicitly-set image(s)): "
                f"black={avg['black']:.2f}, "
                f"white={avg['white']:.2f}"
            )

        self.exposure_mode_label.configure(
            text=mode_text
        )

        if using_forced_black_preview:
            self.numeric_label.configure(
                text=(
                    f"{channel}: PREVIEW black=0.00, white={white:.2f}  "
                    f"(temporary landmark/calibration mode)\n"
                    f"Saved slider values: black={slider_black:.2f}, "
                    f"white={slider_white:.2f}. "
                    "Below black = exactly 0; above white = exactly 1."
                )
            )
        else:
            self.numeric_label.configure(
                text=(
                    f"{channel}: black={black:.2f}, "
                    f"white={white:.2f}\n"
                    "Below black = exactly 0; above white = exactly 1."
                )
            )

        placed = self.manual_landmarks_yx[
            self.current_file_index
        ]

        status_parts = []

        for key, cfg in MANUAL_GUI_LANDMARKS.items():
            if key in placed:
                y, x = placed[
                    key
                ]
                status_parts.append(
                    f"{key}=({x:.0f},{y:.0f})"
                )
            else:
                status_parts.append(
                    f"{key}=NOT SET"
                )

        rotation_ccw_deg = compute_counterclockwise_rotation_to_vertical_deg(
            placed
        )
        if rotation_ccw_deg is None:
            status_parts.append("rotation CCW-only to straight = NOT SET")
            self.rotation_label.configure(
                text="Rotation CCW-only to straight: NOT SET"
            )
        else:
            status_parts.append(
                f"rotation CCW-only to straight = {rotation_ccw_deg:.2f} deg"
            )
            self.rotation_label.configure(
                text=(
                    "Rotation CCW-only to straight: "
                    f"{rotation_ccw_deg:.2f}°"
                )
            )

        self.landmark_status_label.configure(
            text="\n".join(
                status_parts
            )
        )

        if mip is None:
            self.preview_native_pil = None
            self.preview_image_item = None
            self.preview_canvas.delete(
                "all"
            )
            self.preview_canvas.create_text(
                20,
                20,
                anchor="nw",
                fill="white",
                text=(
                    f"Channel {channel!r} is absent "
                    "from this image."
                ),
            )
            self.hist_canvas.delete(
                "all"
            )
            return

        self._draw_histogram(
            mip,
            black,
            white,
        )

        if white <= black:
            self.preview_native_pil = None
            self.preview_image_item = None
            self.preview_canvas.delete(
                "all"
            )
            self.preview_canvas.create_text(
                20,
                20,
                anchor="nw",
                fill="white",
                text=(
                    "White point must be greater "
                    "than black point."
                ),
            )
            return

        windowed = apply_manual_exposure(
            mip,
            black,
            white,
        )

        overlay_masks = None
        overlay_centers = None

        preview_key = (
            int(self.current_file_index),
            str(channel),
        )
        if bool(self.show_cellpose_preview_var.get()):
            cached_test = self.cellpose_preview_results.get(
                preview_key
            )
            if cached_test is not None:
                overlay_masks, overlay_centers, kept_count, total_count = (
                    self._filtered_cellpose_preview(
                        cached_test,
                        channel=channel,
                    )
                )
                self.test_label.configure(
                    text=(
                        f"Cellpose preview: {kept_count}/{total_count} instances "
                        "inside the active rectangle, anatomical region, and "
                        "custom ROI rules. Magenta=boundary; yellow=centroid."
                    )
                )

        self._preview_rgb(
            windowed,
            masks=overlay_masks,
            centers=overlay_centers,
        )
        self._render_cached_preview_to_canvas()

    def toggle_cellpose_preview(self):
        """Show/hide cached Cellpose results without rerunning Cellpose."""
        self.refresh_preview()


    # ------------------------------------------------------------------
    # Cellpose test
    # ------------------------------------------------------------------

    def _set_cellpose_busy_cursor(self):
        """Show the Windows wait/hourglass cursor over the entire GUI."""
        self._busy_cursor_restore = {}

        def apply(widget):
            try:
                previous = widget.cget("cursor")
                self._busy_cursor_restore[widget] = previous
                widget.configure(cursor="wait")
            except Exception:
                pass

            try:
                children = widget.winfo_children()
            except Exception:
                children = []

            for child in children:
                apply(child)

        apply(self.root)
        self.root.update_idletasks()


    def _restore_cellpose_cursor(self):
        """Restore each widget's cursor after background Cellpose finishes."""
        restore = self._busy_cursor_restore
        self._busy_cursor_restore = {}

        for widget, previous in list(restore.items()):
            try:
                if widget.winfo_exists():
                    widget.configure(cursor=previous)
            except Exception:
                pass

        try:
            self.root.configure(cursor="")
        except Exception:
            pass


    def _run_cellpose_test_worker(
        self,
        channel,
        mip,
        black,
        white,
    ):
        """Heavy Cellpose test work executed outside the Tkinter thread."""
        windowed = apply_manual_exposure(
            mip,
            black,
            white,
        )

        masks, centers, areas, accepted_labels = (
            run_windowed_cellpose_instances(
                self.loaded_models[
                    channel
                ],
                windowed,
                SPOT_SETTINGS[
                    channel
                ],
                return_labels=True,
            )
        )

        return {
            "windowed": windowed,
            "masks": masks,
            "centers": centers,
            "areas": areas,
            "accepted_labels": accepted_labels,
        }


    def _schedule_cellpose_test_poll(self):
        if self._cellpose_test_poll_after_id is not None:
            return

        self._cellpose_test_poll_after_id = self.root.after(
            max(25, int(GUI_TEST_CELLPPOSE_POLL_MS)),
            self._poll_cellpose_test,
        )


    def _poll_cellpose_test(self):
        self._cellpose_test_poll_after_id = None

        future = self.cellpose_test_future
        if future is None:
            return

        if not future.done():
            elapsed = 0.0
            if self.cellpose_test_started_at is not None:
                elapsed = time.monotonic() - self.cellpose_test_started_at

            self.test_busy_label.configure(
                text=(
                    "Cellpose is running on the GPU… "
                    f"{elapsed:.0f} s elapsed. "
                    "The GUI will remain responsive."
                )
            )
            self._schedule_cellpose_test_poll()
            return

        context = self.cellpose_test_context or {}
        self.cellpose_test_future = None
        self.cellpose_test_context = None

        try:
            result = future.result()

            # Ignore a stale result if the user navigated to another image or
            # channel while the test was running.
            if (
                int(self.current_file_index) != int(context.get("file_index", -1))
                or str(self.current_channel) != str(context.get("channel", ""))
            ):
                self.test_label.configure(
                    text=(
                        "Cellpose test finished, but the displayed image/channel "
                        "changed while it was running. Result was not overlaid."
                    )
                )
                return

            windowed = result["windowed"]
            masks = result["masks"]
            centers = result["centers"]
            areas = result["areas"]
            accepted_labels = result["accepted_labels"]

            preview_key = (
                int(context["file_index"]),
                str(context["channel"]),
            )
            self.cellpose_preview_results[preview_key] = {
                "masks": masks,
                "centers": centers,
                "areas": areas,
                "accepted_labels": accepted_labels,
                "black": float(context["black"]),
                "white": float(context["white"]),
            }

            self.show_cellpose_preview_var.set(True)
            self.refresh_preview()

            if len(areas):
                area_text = (
                    f"; median area={np.median(areas):.1f}px"
                )
            else:
                area_text = ""

            elapsed = 0.0
            if self.cellpose_test_started_at is not None:
                elapsed = time.monotonic() - self.cellpose_test_started_at

            _preview_masks, _preview_centers, kept_count, total_count = (
                self._filtered_cellpose_preview(
                    self.cellpose_preview_results[preview_key],
                    channel=context["channel"],
                )
            )

            self.test_label.configure(
                text=(
                    f"Test result: {kept_count}/{total_count} Cellpose instances "
                    "inside the active counting areas"
                    f"{area_text}. Completed in {elapsed:.1f} s. "
                    "Magenta=instance boundary; yellow=Cellpose centroid. "
                    "Manual colored dots remain the ce/si/bo/to positions."
                )
            )

        except Exception as exc:
            self.messagebox.showerror(
                "Cellpose test failed",
                str(exc),
            )

        finally:
            self.cellpose_test_started_at = None
            self.test_progress.stop()
            self.test_busy_label.configure(text="")
            try:
                self.test_cellpose_button.state(["!disabled"])
            except Exception:
                pass
            self._restore_cellpose_cursor()


    def test_cellpose(
        self,
    ):
        if self.cellpose_test_future is not None:
            if not self.cellpose_test_future.done():
                return

        channel = self.current_channel
        file_index = int(self.current_file_index)
        ims_path = self.ims_files[
            file_index
        ]

        mip = self._get_mip(
            file_index,
            channel,
        )

        if mip is _MIP_LOADING:
            self.test_busy_label.configure(
                text="Waiting for the full-resolution MIP to finish preloading…"
            )
            return

        if mip is None:
            self.messagebox.showwarning(
                "Channel unavailable",
                f"{channel!r} is not present in {ims_path.name}.",
            )
            return

        if channel not in self.loaded_models:
            self.messagebox.showerror(
                "Model unavailable",
                f"No Cellpose model is loaded for {channel!r}.",
            )
            return

        (
            black,
            white,
            _using_forced_black_preview,
            _slider_black,
            _slider_white,
        ) = self._preview_black_white(mip)

        if white <= black:
            self.messagebox.showerror(
                "Invalid exposure",
                "White point must be greater than black point.",
            )
            return

        self.test_cellpose_button.state(["disabled"])
        self.test_progress.start(10)
        self.test_busy_label.configure(
            text="Starting Cellpose on the GPU…"
        )
        self.test_label.configure(
            text=(
                "Cellpose test is running in the background. "
                "You can still move the window and interact with the GUI."
            )
        )
        self._set_cellpose_busy_cursor()

        self.cellpose_test_started_at = time.monotonic()
        self.cellpose_test_context = {
            "file_index": file_index,
            "channel": str(channel),
            "black": black,
            "white": white,
        }

        self.cellpose_test_future = self.cellpose_test_executor.submit(
            self._run_cellpose_test_worker,
            channel,
            mip,
            black,
            white,
        )
        self._schedule_cellpose_test_poll()


    def _collect_current_settings(self):
        """Build a JSON-safe snapshot, including incomplete work in progress."""
        series_average = {
            channel: self._series_average(channel)
            for channel in CHANNEL_PROCESSING_ORDER
        }
        per_file = {}
        for file_index, ims_path in enumerate(self.ims_files):
            file_values = {}
            for channel in CHANNEL_PROCESSING_ORDER:
                effective = self._effective_exposure(file_index, channel)
                if effective["white"] <= effective["black"]:
                    raise ValueError(
                        f"{ims_path.name} / {channel}: white point must exceed "
                        "black point."
                    )
                file_values[channel] = {
                    "black": float(effective["black"]),
                    "white": float(effective["white"]),
                    "source": str(effective["source"]),
                }
            per_file[ims_path.name] = file_values

        landmarks = {}
        rotations = {}
        for file_index, ims_path in enumerate(self.ims_files):
            points = self.manual_landmarks_yx[file_index]
            landmarks[ims_path.name] = {
                key: [float(points[key][0]), float(points[key][1])]
                for key in MANUAL_GUI_LANDMARKS
                if key in points
            }
            rotation_deg = compute_counterclockwise_rotation_to_vertical_deg(points)
            if rotation_deg is not None:
                rotations[ims_path.name] = {
                    "counterclockwise_to_vertical_deg_ccw_only": float(rotation_deg),
                    "group_name": format_rotation_group_name(rotation_deg),
                }

        custom_counting_rois_yx = {
            ims_path.name: {
                channel: {
                    hemisphere: [
                        [float(y), float(x)]
                        for y, x in self.custom_counting_rois_yx.get(
                            (file_index, channel, hemisphere), []
                        )
                    ]
                    for hemisphere in ("L", "R")
                    if len(self.custom_counting_rois_yx.get(
                        (file_index, channel, hemisphere), []
                    )) >= CUSTOM_ROI_MIN_VERTICES
                }
                for channel in CHANNEL_PROCESSING_ORDER
                if any(
                    len(self.custom_counting_rois_yx.get(
                        (file_index, channel, hemisphere), []
                    )) >= CUSTOM_ROI_MIN_VERTICES
                    for hemisphere in ("L", "R")
                )
            }
            for file_index, ims_path in enumerate(self.ims_files)
        }
        custom_counting_roi_modes = {
            ims_path.name: {
                channel: {
                    hemisphere: str(self.custom_counting_roi_modes.get(
                        (file_index, channel, hemisphere),
                        DEFAULT_CUSTOM_ROI_MODE,
                    ))
                    for hemisphere in ("L", "R")
                    if len(self.custom_counting_rois_yx.get(
                        (file_index, channel, hemisphere), []
                    )) >= CUSTOM_ROI_MIN_VERTICES
                }
                for channel in CHANNEL_PROCESSING_ORDER
                if any(
                    len(self.custom_counting_rois_yx.get(
                        (file_index, channel, hemisphere), []
                    )) >= CUSTOM_ROI_MIN_VERTICES
                    for hemisphere in ("L", "R")
                )
            }
            for file_index, ims_path in enumerate(self.ims_files)
        }

        counting_regions = {}
        for channel in CHANNEL_PROCESSING_ORDER:
            region = str(self.channel_counting_regions.get(
                channel, DEFAULT_COUNTING_REGION
            )).strip().lower()
            if region not in COUNTING_REGION_MODES:
                region = DEFAULT_COUNTING_REGION
            counting_regions[channel] = region

        return {
            "series_average": series_average,
            "per_file": per_file,
            "manual_landmarks_yx": landmarks,
            "rotation": rotations,
            "enabled_channels": [
                channel
                for channel in CHANNEL_PROCESSING_ORDER
                if bool(self.channel_enabled_vars[channel].get())
            ],
            "counting_regions": counting_regions,
            "custom_counting_rois_yx": custom_counting_rois_yx,
            "custom_counting_roi_modes": custom_counting_roi_modes,
        }

    def save_window_settings_json(self, closing=False):
        """Save a resumable snapshot without closing or requiring completion."""
        selected_path = self.filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Neurodot settings",
            initialdir=str(EXPOSURE_SETTINGS_JSON.parent),
            initialfile=EXPOSURE_SETTINGS_JSON.name,
            defaultextension=".json",
            filetypes=[("JSON settings", "*.json"), ("All files", "*.*")],
        )
        if not selected_path:
            return False
        try:
            snapshot = self._collect_current_settings()
            saved_path = _save_exposure_settings(
                snapshot,
                self.ims_files,
                destination=selected_path,
            )
        except Exception as exc:
            self.messagebox.showerror(
                "Could not save settings",
                f"The settings JSON could not be saved:\n\n{exc}",
            )
            return False
        if not closing:
            self.messagebox.showinfo(
                "Settings saved",
                f"Current work was saved to:\n\n{saved_path.resolve()}\n\n"
                "You can continue editing or close Neurodot later.",
            )
        return True

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    def accept(
        self,
    ):
        # Validate all required downstream landmark positions for every image.
        missing = []

        for i, ims_path in enumerate(
            self.ims_files
        ):
            for key in MANUAL_GUI_LANDMARKS:
                if (
                    key
                    not in self.manual_landmarks_yx[
                        i
                    ]
                ):
                    missing.append(
                        f"{ims_path.name}: {key}"
                    )

        if missing:
            preview = "\n".join(
                missing[
                    :12
                ]
            )

            if len(
                missing
            ) > 12:
                preview += (
                    f"\n... and {len(missing) - 12} more"
                )

            self.messagebox.showerror(
                "Landmarks missing",
                "Each image needs both midline points, their derived/editable "
                "centre (ce), and si/bo/to for both L and R.\n\n"
                + preview,
            )
            return

        series_average = {
            channel: self._series_average(
                channel
            )
            for channel in CHANNEL_PROCESSING_ORDER
        }

        per_file = {}

        for i, ims_path in enumerate(
            self.ims_files
        ):
            file_values = {}

            for channel in CHANNEL_PROCESSING_ORDER:
                effective = self._effective_exposure(
                    i,
                    channel,
                )

                if (
                    effective[
                        "white"
                    ]
                    <= effective[
                        "black"
                    ]
                ):
                    self.messagebox.showerror(
                        "Invalid exposure",
                        f"{ims_path.name} / {channel}: "
                        "white point must exceed black point.",
                    )
                    return

                file_values[
                    channel
                ] = {
                    "black": float(
                        effective[
                            "black"
                        ]
                    ),
                    "white": float(
                        effective[
                            "white"
                        ]
                    ),
                    "source": str(
                        effective[
                            "source"
                        ]
                    ),
                }

            per_file[
                ims_path.name
            ] = file_values

        landmarks = {}

        for i, ims_path in enumerate(
            self.ims_files
        ):
            landmarks[
                ims_path.name
            ] = {
                key: [
                    float(
                        self.manual_landmarks_yx[
                            i
                        ][
                            key
                        ][
                            0
                        ]
                    ),
                    float(
                        self.manual_landmarks_yx[
                            i
                        ][
                            key
                        ][
                            1
                        ]
                    ),
                ]
                for key in MANUAL_GUI_LANDMARKS
            }

        rotations = {
            ims_path.name: {
                "counterclockwise_to_vertical_deg_ccw_only": float(
                    compute_counterclockwise_rotation_to_vertical_deg(
                        self.manual_landmarks_yx[i]
                    )
                ),
                "group_name": format_rotation_group_name(
                    compute_counterclockwise_rotation_to_vertical_deg(
                        self.manual_landmarks_yx[i]
                    )
                ),
            }
            for i, ims_path in enumerate(self.ims_files)
        }
        custom_counting_roi_modes = {
            ims_path.name: {
                channel: {
                    hemisphere: str(self.custom_counting_roi_modes.get(
                        (i, channel, hemisphere),
                        DEFAULT_CUSTOM_ROI_MODE,
                    ))
                    for hemisphere in ("L", "R")
                    if len(self.custom_counting_rois_yx.get(
                        (i, channel, hemisphere), []
                    )) >= CUSTOM_ROI_MIN_VERTICES
                }
                for channel in CHANNEL_PROCESSING_ORDER
                if any(
                    len(self.custom_counting_rois_yx.get(
                        (i, channel, hemisphere), []
                    )) >= CUSTOM_ROI_MIN_VERTICES
                    for hemisphere in ("L", "R")
                )
            }
            for i, ims_path in enumerate(self.ims_files)
        }

        custom_counting_rois_yx = {
            ims_path.name: {
                channel: {
                    hemisphere: [
                        [float(y), float(x)]
                        for y, x in self.custom_counting_rois_yx.get(
                            (i, channel, hemisphere),
                            [],
                        )
                    ]
                    for hemisphere in ("L", "R")
                    if len(
                        self.custom_counting_rois_yx.get(
                            (i, channel, hemisphere),
                            [],
                        )
                    ) >= CUSTOM_ROI_MIN_VERTICES
                }
                for channel in CHANNEL_PROCESSING_ORDER
                if any(
                    len(
                        self.custom_counting_rois_yx.get(
                            (i, channel, hemisphere),
                            [],
                        )
                    ) >= CUSTOM_ROI_MIN_VERTICES
                    for hemisphere in ("L", "R")
                )
            }
            for i, ims_path in enumerate(self.ims_files)
        }

        enabled_channels = [
            channel
            for channel in CHANNEL_PROCESSING_ORDER
            if bool(self.channel_enabled_vars[channel].get())
        ]

        counting_regions = {}
        for channel in CHANNEL_PROCESSING_ORDER:
            region = str(
                self.channel_counting_regions.get(
                    channel,
                    DEFAULT_COUNTING_REGION,
                )
            ).strip().lower()
            if region not in COUNTING_REGION_MODES:
                region = DEFAULT_COUNTING_REGION
            counting_regions[channel] = region

        self.result = {
            "series_average": series_average,
            "per_file": per_file,
            "manual_landmarks_yx": landmarks,
            "rotation": rotations,
            "enabled_channels": enabled_channels,
            "counting_regions": counting_regions,
            "custom_counting_rois_yx": custom_counting_rois_yx,
            "custom_counting_roi_modes": custom_counting_roi_modes,
        }

        self.accepted = True
        self._stop_logo_video()
        try:
            self.mip_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        try:
            self.cellpose_test_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        self.root.destroy()

    def request_close(self):
        """Offer to save resumable work before intentionally closing."""
        choice = self.messagebox.askyesnocancel(
            "Close Neurodot?",
            "Save the current settings before closing?\n\n"
            "Yes: choose a JSON file, save, and close.\n"
            "No: close without saving.\n"
            "Cancel: return to Neurodot.",
            parent=self.root,
            default="cancel",
            icon="question",
        )
        if choice is None:
            return
        if choice and not self.save_window_settings_json(closing=True):
            # Cancelling the file picker or encountering a save error keeps
            # the main window open, so work cannot be lost accidentally.
            return
        self.cancel()

    def cancel(
        self,
    ):
        self.accepted = False
        self.result = None
        self._stop_logo_video()
        try:
            self.mip_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        try:
            self.cellpose_test_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        self.root.destroy()

    def run(
        self,
    ):
        self.root.update_idletasks()
        self.root.deiconify()

        # Start maximized only after every dark-themed widget is ready. Keep
        # the explicit geometry from __init__ as the fallback.
        try:
            self.root.state("zoomed")
        except Exception:
            try:
                self.root.attributes("-zoomed", True)
            except Exception:
                pass

        self.root.lift()
        self.root.focus_force()
        self.root.mainloop()

        return self.result



def choose_batch_exposure_settings(ims_files, loaded_models, progress=None):
    import gc

    try:
        if progress is not None:
            progress.update(
                "Opening the image interface...",
                "The IMS preview loader will appear next.",
            )
            # Never keep two independent Tk roots alive. Pillow image handles
            # are interpreter-specific and can otherwise fail as "pyimageN
            # doesn't exist" when the main GUI is initialized.
            progress.close()
        gui = ExposureWindowGUI(
            ims_files=ims_files,
            loaded_models=loaded_models,
        )
        result = gui.run()

        # The GUI owns many Tk Variable and PhotoImage objects. Destroy those
        # Python wrappers now, on Tk's main thread, before batch processing is
        # handed to a worker. Otherwise cyclic garbage collection can invoke
        # their destructors from that worker and produce "main thread is not
        # in main loop" errors during Imaris output writing.
        del gui
        gc.collect()
        return result
    except ImportError as exc:
        raise RuntimeError(
            "The exposure GUI requires tkinter and Pillow (PIL). "
            f"Missing dependency: {exc}"
        )



__all__ = [name for name in globals() if not name.startswith("__")]
