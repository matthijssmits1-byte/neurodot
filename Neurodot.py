#!/usr/bin/env python
"""Neurodot: optional self-contained version of the modular app.

Generated from src/neurodot by tools/build_monolith.py.
Edit the modular source, then regenerate this file.
"""
# This file intentionally contains the complete application.
# The modular source remains the maintained source of truth.


# ============================================================================
# BEGIN GENERATED MODULE: paths.py
# ============================================================================

"""Filesystem locations that work from source and from a frozen application."""

from pathlib import Path
import sys


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT)).resolve()


def runtime_data_root():
    """Writable working directory for source runs or installed builds."""
    if getattr(sys, "frozen", False):
        return Path.home() / "Documents" / "Neurodot"
    return PROJECT_ROOT


RUNTIME_DATA_ROOT = runtime_data_root()


def resolve_resource(relative_path, legacy_relative_path=None):
    """Resolve the first existing named resource, preferring the primary name.

    Both names remain inside this project's ``resources`` directory. The
    optional second name supports established assets whose filename differs
    from the current preferred filename, without falling back to an unrelated
    legacy workspace.
    """
    primary = BUNDLE_ROOT / "resources" / Path(relative_path)
    if primary.exists() or legacy_relative_path is None:
        return primary

    fallback = BUNDLE_ROOT / "resources" / Path(legacy_relative_path)
    if fallback.exists():
        return fallback
    return primary


def executable_dir():
    """Directory containing the installed executable, or the project root."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def configure_windows_app_identity():
    """Give all Neurodot windows one explicit Windows taskbar identity."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Neurodot.AdvancedCellDetection"
        )
    except Exception:
        pass


# ============================================================================
# BEGIN GENERATED MODULE: config.py
# ============================================================================

"""Application configuration and stable defaults."""
from pathlib import Path
import math
import warnings

# =============================================================================
# CONFIGURATION
# =============================================================================

warnings.filterwarnings("ignore", category=FutureWarning)

IMS_INPUT_DIR = RUNTIME_DATA_ROOT / "data" / "input"
OUTPUT_SCENE_DIR = RUNTIME_DATA_ROOT / "data" / "output"

# Whole, known-good Imaris donor containing all eight Spot groups:
#   Points0=g, Points1=b, Points2=r, Points3=405,
#   Points4=ce, Points5=bo, Points6=si, Points7=to.
#
# The first four are populated by the models.
# The last four are copied exactly from the donor and intentionally remain empty
# for manual annotation in Imaris.
SCHEMA_DONOR_IMS = resolve_resource(
    "templates/donor_1_point_each_with_to.ims",
    "start_scene/donor_1_point_each_with_to.ims",
)

# Cellpose model selection.
#
# Leave CELLPOSE_MODEL_PATH empty to use Cellpose's built-in/native cpsam_v2.
# To use a local model file instead, set the full or relative path, e.g.:
#   CELLPOSE_MODEL_PATH = r"./models/cpsam_v2"
#   CELLPOSE_MODEL_PATH = r"D:\models\cpsam_v2"
#
# The selected model is loaded once and shared across all fluorescence channels.
CELLPOSE_MODEL_PATH = str(
    resolve_resource(
        "models/cpsam_v2",
        "models/cpsam_v2_sweeney",
    )
)
NATIVE_CELLPPOSE_MODEL = "cpsam_v2"

# Groups populated automatically by the models.
# Predicted Imaris Spot display size.
# Requested diameter = 5 um -> radius = 2.5 um.
# Physical Spot diameter stored in Scene/Scene8.
PREDICTED_SPOT_DIAMETER_UM = 5.0
PREDICTED_SPOT_RADIUS_UM = PREDICTED_SPOT_DIAMETER_UM / 2.0

# Predicted Spots remain center points. Imaris stores their visible width in
# screen pixels rather than physical units, so follow the selected diameter
# numerically (for example, 10 um diameter -> 10 px center-point width).
PREDICTED_CENTER_POINT_SIZE_PX = max(
    1,
    int(round(PREDICTED_SPOT_DIAMETER_UM)),
)

# Empty predicted groups must contain one schema-preserving placeholder, but
# placeholders from different channels must not look colocalized downstream.
PLACEHOLDER_COLOCALIZATION_THRESHOLD_UM = 3.5
PLACEHOLDER_SPACING_UM = 5.0

PREDICTED_GROUPS = [
    {"name": "g",   "container": "Points0", "id": 200001, "radius_um": PREDICTED_SPOT_RADIUS_UM},
    {"name": "b",   "container": "Points1", "id": 200002, "radius_um": PREDICTED_SPOT_RADIUS_UM},
    {"name": "r",   "container": "Points2", "id": 200003, "radius_um": PREDICTED_SPOT_RADIUS_UM},
    {"name": "405", "container": "Points3", "id": 200004, "radius_um": PREDICTED_SPOT_RADIUS_UM},
]

# Manual-only groups. These are copied from the donor exactly as Imaris created
# them and are deliberately NOT populated by this pipeline.
MANUAL_EMPTY_GROUPS = [
    {"name": "ce",  "container": "Points4", "id": 200005},
    {"name": "bo",  "container": "Points5", "id": 200006},
    {"name": "si",  "container": "Points6", "id": 200007},
    {"name": "to",  "container": "Points7", "id": 200008},
    {
        "name": "rot",
        "container": "Points8",
        "id": 200009,
        "clone_from_container": "Points4",
        "clone_from_id": 200005,
        "dynamic_name": True,
    },
]

# Full donor/viewer order.
GROUPS = PREDICTED_GROUPS + MANUAL_EMPTY_GROUPS


# =============================================================================
# OUTPUT FILE NAMING
# =============================================================================
#
# Customize only the middle tag of generated filenames. The hemisphere suffixes
# _L and _R are always preserved.
#
# Examples:
#   OUTPUT_FILE_TAG = "_counted"  -> sample_counted_L.ims / sample_counted_R.ims
#   OUTPUT_FILE_TAG = "_cells"    -> sample_cells_L.ims   / sample_cells_R.ims
#   OUTPUT_FILE_TAG = ""          -> sample_L.ims         / sample_R.ims
OUTPUT_FILE_TAG = "_MS"


# =============================================================================
# GUI THEME / GRAPHICS
# =============================================================================
# Optional branding files. If either file is absent, the GUI still works.
GRAPHICS_DIR = resolve_resource("graphics/Icon.png", "graphics/Icon.png").parent
GUI_ICON_PATH = GRAPHICS_DIR / "Icon.png"
GUI_ICON_ICO_PATH = GRAPHICS_DIR / "Icon.ico"

# Bottom-right Neurodot branding. The MP4 is preferred and loops continuously.
# The static image is retained only as a fallback if the video cannot be opened
# (for example if OpenCV is not installed).
GUI_VIDEO_PATH = GRAPHICS_DIR / "Neurodot_rotating.mp4"
GUI_BANNER_PATH = GRAPHICS_DIR / "Theme_with_subtitle.png"
GUI_SHOW_BANNER = True
GUI_BANNER_MAX_WIDTH = 185
GUI_BANNER_MAX_HEIGHT = 300
GUI_VIDEO_FPS_FALLBACK = 24.0

# Restrained dark GUI palette. Green is used only as a subtle accent.
# These settings affect only the Tkinter interface, not the
# microscopy image, Cellpose inputs, output .ims files, or Spot colours.
GUI_BG = "#07090b"
GUI_PANEL_BG = "#0d1114"
GUI_CONTROL_BG = "#151a1e"
GUI_CONTROL_ACTIVE_BG = "#20272c"
GUI_FG = "#edf2f4"
GUI_MUTED_FG = "#8f9aa1"
GUI_ACCENT = "#54d96b"
GUI_BORDER = "#2b353b"

# Landmark-derived counting inclusion rectangles. Cellpose still runs on the
# complete displayed image; detections outside the appropriate L/R rectangle
# are removed afterward. No padding is applied: the landmark-defined edges are
# now the exact counting boundaries.
COUNTING_ROI_MARGIN_PX = 0.0
COUNTING_ROI_DASH_PX = 7
COUNTING_ROI_GAP_PX = 5
COUNTING_ROI_GUI_COLOR = "#54d96b"

# Native-image landmark label rendering. The actual font size is scaled from
# the image dimensions within these bounds so it remains legible after the
# preview is fitted to the window.
LANDMARK_LABEL_FONT_MIN_PX = 13
LANDMARK_LABEL_FONT_MAX_PX = 24
LANDMARK_LABEL_FONT_FRACTION = 0.011
LANDMARK_LABEL_GAP_PX = 5

# Per-channel, series-wide anatomical subregion selection. "whole" preserves
# established behavior for that channel.
# Dorsal and ventral are evaluated along the directed bottom -> top midline,
# so the choice remains anatomical rather than depending on screen rotation.
COUNTING_REGION_MODES = ("whole", "dorsal", "ventral")
DEFAULT_COUNTING_REGION = "whole"
COUNTING_DIVIDER_GUI_COLOR = "#00d9ff"
CUSTOM_ROI_COLORS = {
    "L": {
        "outline": "#39c5ff",
        "fill": (57, 197, 255, 42),
    },
    "R": {
        "outline": "#ffad42",
        "fill": (255, 173, 66, 42),
    },
}
CUSTOM_ROI_EXCLUSION_COLOR = {
    "outline": "#ff5a5a",
    "fill": (255, 90, 90, 28),
}
CUSTOM_ROI_MODES = ("include", "exclude")
DEFAULT_CUSTOM_ROI_MODE = "include"
CUSTOM_ROI_MIN_SAMPLE_DISTANCE_PX = 2.0
CUSTOM_ROI_MIN_VERTICES = 3

# Reset the saved Imaris Surpass camera to a fitted image-centred view when
# writing each output. This prevents a stale camera from another .ims file
# opening on empty space.
RESET_IMARIS_CAMERA_ON_EXPORT = True


# =============================================================================
# Z PLACEMENT
# =============================================================================
#
# The detector is fundamentally 2D (it operates on a maximum-intensity
# projection). For visual 2D counting in Imaris, placing every Spot at the
# physical center of the Z stack avoids perspective/parallax displacement when
# the 3D view is tilted.
#
# Options:
#   "stack_center"  -> recommended for this pipeline; all spots share the exact
#                      physical midpoint Z = (ExtMin2 + ExtMax2) / 2.
#   "optical"       -> estimate a separate Z from the raw fluorescence stack.
#
Z_PLACEMENT_MODE = "stack_center"

# Optional physical offset from the stack center, in micrometres.
# Leave at 0.0 unless you deliberately want the dots slightly above/below
# the middle plane.
Z_CENTER_OFFSET_UM = 0.0

CHANNEL_PROCESSING_ORDER = ["g", "b", "r", "405"]

# MUST stay aligned with Step 1 training-data export.
TARGET_CONFIG = {
    "g":   {"aliases": ["g", "gfp", "green"],          "prefix": "5", "wl": 525.0},
    "r":   {"aliases": ["m", "mcherry", "cy3", "red"], "prefix": "6", "wl": 600.0},
    "b":   {"aliases": ["c", "cy5", "far", "b"],        "prefix": "7", "wl": 708.0},
    "405": {"aliases": ["d", "dapi", "blue", "405"],    "prefix": "4", "wl": 447.0},
}

# Authoritative emission-wavelength bands for mapping physical Imaris channels
# to Neurodot logical groups. The intervals are continuous and non-overlapping:
#
#   405 : wavelength < 482 nm
#   g   : 482 <= wavelength < 551 nm
#   r   : 551 <= wavelength < 641 nm
#   b   : wavelength >= 641 nm
#
# If a usable emission wavelength exists it ALWAYS wins. Channel-name aliases
# are used only when wavelength metadata is absent/unparseable.
CHANNEL_WAVELENGTH_BANDS_NM = {
    "405": (None, 482.0),
    "g":   (482.0, 551.0),
    "r":   (551.0, 641.0),
    "b":   (641.0, None),
}

# =============================================================================
# CELLPOSE CANDIDATES + PER-CHANNEL CANDIDATE-POPULATION GATE
# =============================================================================
#
# Philosophy
# ----------
# Cellpose is deliberately permissive and proposes morphologically plausible
# cell centers.
#
# Fluorescence acceptance is then determined from the DISTRIBUTION OF CANDIDATE
# CELL-BODY INTENSITIES in that channel/image.
#
# This is much closer to manual Imaris counting:
#   - dim/autofluorescent candidate objects form one population;
#   - genuinely positive cells form a brighter population;
#   - the threshold is learned independently for every channel and image.
#
# No candidate is compared with neighboring cells, so a bright cell surrounded
# by even brighter cells is not penalized.
#
# Very permissive Cellpose threshold: fluorescence filtering is expected to do
# most of the rejection.
PREDICTION_MIN_CONFIDENCE = 0.05

# Candidate-cell fluorescence settings.
#
# For each Cellpose candidate we measure the stated percentile within a small
# central disk. The values are log-transformed and fit with a two-component
# Gaussian mixture:
#       low-intensity component  -> autofluorescent / negative
#       high-intensity component -> positive
#
# The decision boundary lies between the two fitted component means.
#
# threshold_fraction:
#   0.50 = halfway between dim and bright population centers.
#   >0.50 = stricter (closer to bright population).
#   <0.50 = more recall-biased.
#
# min_separation_sigma:
#   if the two fitted populations are not genuinely separated, fall back to a
#   conservative percentile threshold rather than pretending a clean bimodal
#   split exists.
#
CANDIDATE_GATE_SETTINGS = {
    "g": {
        "signal_radius_px": 5,
        "signal_percentile": 70.0,
        "threshold_fraction": 0.55,
        "min_separation_sigma": 1.0,
        "fallback_percentile": 55.0,
    },
    "b": {
        "signal_radius_px": 5,
        "signal_percentile": 70.0,
        "threshold_fraction": 0.55,
        "min_separation_sigma": 1.0,
        "fallback_percentile": 55.0,
    },
    "r": {
        "signal_radius_px": 5,
        "signal_percentile": 70.0,
        "threshold_fraction": 0.55,
        "min_separation_sigma": 1.0,
        "fallback_percentile": 55.0,
    },
    "405": {
        "signal_radius_px": 5,
        "signal_percentile": 70.0,
        "threshold_fraction": 0.55,
        "min_separation_sigma": 1.0,
        "fallback_percentile": 55.0,
    },
}


# Detection settings intentionally mirror Step 3.
SPOT_SETTINGS = {
    "g": {
        "native_model": NATIVE_CELLPPOSE_MODEL,
        "model_radius_px": 8.0,
        "min_confidence": PREDICTION_MIN_CONFIDENCE,
        "min_distance_px": 6,

        # Same local XY refinement as Step 3.
        "refine_search_radius_px": 10,
        "refine_gaussian_sigma_px": 5.0,
        "refine_image_sigma_px": 1.0,
        "refine_signal_power": 1.5,
        "refine_iterations": 4,
        "max_refine_shift_px": 10.0,

        "z_localization_radius_px": 8,
        "display_radius_um": PREDICTED_SPOT_RADIUS_UM,
    },
    "b": {
        "native_model": NATIVE_CELLPPOSE_MODEL,
        "model_radius_px": 8.0,
        "min_confidence": PREDICTION_MIN_CONFIDENCE,
        "min_distance_px": 6,
        "refine_search_radius_px": 10,
        "refine_gaussian_sigma_px": 5.0,
        "refine_image_sigma_px": 1.0,
        "refine_signal_power": 1.5,
        "refine_iterations": 4,
        "max_refine_shift_px": 10.0,
        "z_localization_radius_px": 8,
        "display_radius_um": PREDICTED_SPOT_RADIUS_UM,
    },
    "r": {
        "native_model": NATIVE_CELLPPOSE_MODEL,
        "model_radius_px": 8.0,
        "min_confidence": PREDICTION_MIN_CONFIDENCE,
        "min_distance_px": 6,
        "refine_search_radius_px": 10,
        "refine_gaussian_sigma_px": 5.0,
        "refine_image_sigma_px": 1.0,
        "refine_signal_power": 1.5,
        "refine_iterations": 4,
        "max_refine_shift_px": 10.0,
        "z_localization_radius_px": 8,
        "display_radius_um": PREDICTED_SPOT_RADIUS_UM,
    },
    "405": {
        "native_model": NATIVE_CELLPPOSE_MODEL,
        "model_radius_px": 7.0,
        "min_confidence": PREDICTION_MIN_CONFIDENCE,
        "min_distance_px": 5,
        "refine_search_radius_px": 9,
        "refine_gaussian_sigma_px": 4.5,
        "refine_image_sigma_px": 1.0,
        "refine_signal_power": 1.5,
        "refine_iterations": 4,
        "max_refine_shift_px": 9.0,
        "z_localization_radius_px": 7,
        "display_radius_um": PREDICTED_SPOT_RADIUS_UM,
    },
}


# =============================================================================
# MANUAL EXPOSURE / CELLPPOSE CONFIG
# =============================================================================

# Cellpose segmentation after manual windowing.  The exposure black point is
# now the primary fluorescence rejection control; these are intentionally much
# less permissive than the old probability-peak detector.
WINDOWED_CELLPOSE_CELLPROB_THRESHOLD = 0.0
WINDOWED_CELLPOSE_FLOW_THRESHOLD = 0.4

# Optional object-size sanity limits.  Leave None to accept Cellpose's own
# segmentation decisions without an additional hand-written area gate.
WINDOWED_MIN_INSTANCE_AREA_PX = None
WINDOWED_MAX_INSTANCE_AREA_PX = None

# GUI / reproducibility.
EXPOSURE_SETTINGS_JSON = OUTPUT_SCENE_DIR / "cellpose_window_settings.json"
EXPOSURE_PREVIEW_MAX_WIDTH = 1600
EXPOSURE_PREVIEW_MAX_HEIGHT = 1000

# Temporary landmark/calibration and series-overview display. These values do
# not overwrite the exposure ultimately used for counting or Imaris metadata.
SETUP_PREVIEW_BLACK = 0.0
SETUP_PREVIEW_WHITE_PERCENTILE = 99.0
SETUP_PREVIEW_WHITE_MIN = 200.0
SETUP_PREVIEW_WHITE_MAX = 400.0

# GUI performance tuning for high-memory workstations.
# Full-resolution MIPs are comparatively small next to the 3D source volumes,
# so keeping many of them resident in RAM makes image/channel navigation fast.
GUI_MIP_CACHE_ITEMS = 64
GUI_MIP_WORKERS = 2

# Warm every image/channel MIP in the background while the user works.
# The cache is automatically enlarged to hold the whole current series when
# this is True.
GUI_PRELOAD_ALL_MIPS = True

# Exposure preview redraws are slightly debounced while dragging sliders.
GUI_PREVIEW_DEBOUNCE_MS = 75

# Preview navigation. Mouse wheel zooms around the cursor; right-drag pans;
# double-right-click returns to the normal fit-to-window view.
GUI_PREVIEW_ZOOM_STEP = 1.20
GUI_PREVIEW_ZOOM_MIN = 1.0
GUI_PREVIEW_ZOOM_MAX = 8.0


# Long sliders + finer raw-intensity increments make manual exposure tuning
# easier. For small dynamic ranges the script still uses 0.01 increments.
GUI_EXPOSURE_SLIDER_LENGTH = 430
GUI_EXPOSURE_FINE_RESOLUTION = 0.01

# Exact adjustment used by the +/- exposure buttons.
GUI_EXPOSURE_BUTTON_STEP = 1.0

# Exposure calibration pickers.
# A click samples the TRUE brightest raw MIP pixel inside this native-image
# radius. Background sets black exactly to that value.
EXPOSURE_PICK_RADIUS_PX = 25

# Weak-positive white point = brightest pixel + a little headroom.
EXPOSURE_POSITIVE_HEADROOM_FRACTION = 0.10
EXPOSURE_POSITIVE_HEADROOM_MIN_RAW = 0.5

EXPOSURE_PICK_BACKGROUND_COLOR = "#00d9ff"
EXPOSURE_PICK_POSITIVE_COLOR = "#ffb347"

# Cellpose test inference runs on its own worker so Tkinter remains responsive.
GUI_TEST_CELLPPOSE_POLL_MS = 100

_MIP_LOADING = object()

# Per-image manual landmark placement in the exposure GUI.
#
# Each output image receives exactly one point in:
#   ce -> centre
#   si -> side landmark
#   bo -> bottom landmark
#   to -> top landmark
#
# The midline is placed first. ``ce`` is then created automatically at its exact
# midpoint before the workflow advances to the bilateral landmarks. It remains
# a normal selectable landmark and can still be cleared/replaced manually.
MANUAL_GUI_LANDMARKS = {
    "rot_bottom": {"label": "bottom midline point", "color": "#ffffff"},
    "rot_top":    {"label": "top midline point",    "color": "#ff4444"},
    "ce":    {"label": "centre (ce)",     "color": "#00ffff"},
    "si_L":  {"label": "si (L)",          "color": "#ff9900"},
    "bo_L":  {"label": "bo (L)",          "color": "#00ff66"},
    "to_L":  {"label": "to (L)",          "color": "#ff33cc"},
    "si_R":  {"label": "si (R)",          "color": "#ffaa55"},
    "bo_R":  {"label": "bo (R)",          "color": "#66ff99"},
    "to_R":  {"label": "to (R)",          "color": "#ff77dd"},
}

EXPOSURE_HISTOGRAM_BINS = 256
EXPOSURE_HISTOGRAM_SAMPLE_PIXELS = 400_000

# GUI starts from robust raw-intensity suggestions only.  These values are NOT
# used automatically after the user confirms the sliders.
DEFAULT_BLACK_PERCENTILE = 1.0
DEFAULT_WHITE_PERCENTILE = 99.8

# If a previously saved JSON exists, use its values as the initial slider
# positions, but still show the GUI for confirmation/editing every run.
LOAD_PREVIOUS_EXPOSURE_SETTINGS = True

ROTATION_LANDMARK_KEYS = ("rot_bottom", "rot_top")


def apply_startup_settings(
    input_dir,
    output_dir,
    output_file_tag,
    model_path,
    spot_diameter_um,
):
    """Apply startup-dialog choices before the processing modules are loaded."""
    global IMS_INPUT_DIR
    global OUTPUT_SCENE_DIR
    global OUTPUT_FILE_TAG
    global CELLPOSE_MODEL_PATH
    global EXPOSURE_SETTINGS_JSON
    global PREDICTED_SPOT_DIAMETER_UM
    global PREDICTED_SPOT_RADIUS_UM
    global PREDICTED_CENTER_POINT_SIZE_PX

    spot_diameter_um = float(spot_diameter_um)
    if not math.isfinite(spot_diameter_um) or spot_diameter_um <= 0.0:
        raise ValueError("Spot diameter must be a finite number greater than zero.")

    IMS_INPUT_DIR = Path(input_dir).expanduser().resolve()
    OUTPUT_SCENE_DIR = Path(output_dir).expanduser().resolve()
    OUTPUT_FILE_TAG = str(output_file_tag)
    CELLPOSE_MODEL_PATH = "" if model_path is None else str(model_path)
    EXPOSURE_SETTINGS_JSON = OUTPUT_SCENE_DIR / "cellpose_window_settings.json"

    # This controls output Spot metadata and rendering only; it deliberately
    # does not alter Cellpose segmentation or detection settings.
    PREDICTED_SPOT_DIAMETER_UM = spot_diameter_um
    PREDICTED_SPOT_RADIUS_UM = spot_diameter_um / 2.0
    PREDICTED_CENTER_POINT_SIZE_PX = max(
        1,
        int(round(spot_diameter_um)),
    )
    for group in PREDICTED_GROUPS:
        group["radius_um"] = PREDICTED_SPOT_RADIUS_UM
    for settings in SPOT_SETTINGS.values():
        settings["display_radius_um"] = PREDICTED_SPOT_RADIUS_UM


# ============================================================================
# BEGIN GENERATED MODULE: common.py
# ============================================================================

"""Shared third-party and standard-library imports for Neurodot."""
from pathlib import Path
import math
import re
import shutil
import warnings
import traceback
import time
from concurrent.futures import ThreadPoolExecutor


# ============================================================================
# BEGIN GENERATED MODULE: imaris_io.py
# ============================================================================

"""Imaris HDF5 scene writing, metadata synchronization, and validation."""
# DONOR VALIDATION / AUTO-DISCOVERY
# =============================================================================

def donor_has_required_groups(path):
    """
    Return (True, details) only if `path` is a valid eight-group donor.

    Required ordering/names:
        Points0 -> g
        Points1 -> b
        Points2 -> r
        Points3 -> 405
        Points4 -> ce
        Points5 -> bo
        Points6 -> si
        Points7 -> to

    Both Scene and Scene8 must contain all eight groups.
    """
    path = Path(path)

    if not path.is_file():
        return False, "file does not exist"

    expected = [
        ("Points0", "g"),
        ("Points1", "b"),
        ("Points2", "r"),
        ("Points3", "405"),
        ("Points4", "ce"),
        ("Points5", "bo"),
        ("Points6", "si"),
        ("Points7", "to"),
    ]

    try:
        with h5py.File(path, "r") as h5:
            for scene_name in ("Scene", "Scene8"):
                content_path = f"{scene_name}/Content"

                if content_path not in h5:
                    return False, f"missing {content_path}"

                content = h5[content_path]

                for container, expected_name in expected:
                    if container not in content:
                        return (
                            False,
                            f"missing {scene_name}/Content/{container}",
                        )

                    actual_name = decode_h5_text(
                        content[container].attrs.get("Name", "")
                    ).strip()

                    if actual_name != expected_name:
                        return (
                            False,
                            f"{scene_name}/Content/{container} has "
                            f"Name={actual_name!r}, expected {expected_name!r}",
                        )

            return True, "valid eight-group donor"

    except Exception as exc:
        return False, f"could not inspect donor: {exc}"


def resolve_schema_donor(configured_path):
    """
    Resolve the eight-group donor BEFORE model inference starts.

    1. Try SCHEMA_DONOR_IMS exactly as configured.
    2. If it is missing or is an older four-group donor, scan its directory
       (normally ./start_scene) for another .ims with the exact eight groups.
    3. Fail with a useful diagnostic if none exists.
    """
    configured_path = Path(configured_path)

    ok, reason = donor_has_required_groups(configured_path)

    if ok:
        return configured_path.resolve()

    print(
        "\nConfigured schema donor is not the required eight-group donor:"
    )
    print(f"  {configured_path.resolve()}")
    print(f"  Reason: {reason}")

    search_dir = configured_path.parent
    candidates = sorted(search_dir.glob("*.ims"))

    valid = []

    for candidate in candidates:
        candidate_ok, candidate_reason = donor_has_required_groups(candidate)

        if candidate_ok:
            valid.append(candidate.resolve())

    if valid:
        chosen = valid[0]

        print(
            "\nAutomatically found a valid eight-group donor:"
        )
        print(f"  {chosen}")

        if len(valid) > 1:
            print(
                f"  ({len(valid)} valid donors found; using the first one)"
            )

        return chosen

    examined = "\n".join(
        f"  - {p.resolve()}"
        for p in candidates
    ) or "  (no .ims files found)"

    raise RuntimeError(
        "\nNo valid eight-group Imaris donor was found.\n\n"
        "The donor must contain, in BOTH Scene/Content and Scene8/Content:\n"
        "  Points0 -> g\n"
        "  Points1 -> b\n"
        "  Points2 -> r\n"
        "  Points3 -> 405\n"
        "  Points4 -> ce\n"
        "  Points5 -> bo\n"
        "  Points6 -> si\n"
        "  Points7 -> to\n\n"
        f"Configured donor:\n  {configured_path.resolve()}\n"
        f"Reason it was rejected:\n  {reason}\n\n"
        f"Files examined in {search_dir.resolve()}:\n{examined}\n\n"
        "Place the supplied Start_Scene_with_to.ims in ./start_scene "
        "and run Step 4 again."
    )


# =============================================================================
# GENERIC HDF5 HELPERS
# =============================================================================

def decode_h5_text(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (bytes, np.bytes_)):
        return bytes(value).decode("utf-8", errors="ignore").rstrip("\x00")

    if isinstance(value, np.ndarray):
        if value.size == 0:
            return ""

        if value.dtype.kind == "S":
            return b"".join(
                bytes(x) for x in value.ravel()
            ).decode("utf-8", errors="ignore").rstrip("\x00")

        if value.dtype.kind == "U":
            return "".join(str(x) for x in value.ravel()).rstrip("\x00")

        if value.dtype.kind in ("u", "i"):
            try:
                return bytes(
                    int(x) for x in value.ravel()
                    if 0 <= int(x) <= 255
                ).decode("utf-8", errors="ignore").rstrip("\x00")
            except Exception:
                pass

        if value.size == 1:
            return decode_h5_text(value.flat[0])

        return str(value)

    if isinstance(value, np.generic):
        return str(value.item())

    return str(value)


def parse_float(value):
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)

    text = decode_h5_text(value)
    m = re.search(
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?",
        text,
    )
    return float(m.group(0)) if m else None


def replace_dataset(group, name, data, dtype=None):
    """
    Imaris commonly stores fixed-shape HDF5 datasets. Delete/recreate rather
    than relying on resize().
    """
    if name in group:
        del group[name]

    if dtype is not None:
        data = np.asarray(data, dtype=dtype)

    return group.create_dataset(name, data=data)


def copy_group_between_files(source_group, target_parent, target_name):
    """
    Copy an entire HDF5 group (attributes + nested datasets) between files.
    """
    if target_name in target_parent:
        del target_parent[target_name]

    source_group.file.copy(
        source_group,
        target_parent,
        name=target_name,
    )

    return target_parent[target_name]


# =============================================================================
# PHYSICAL IMAGE COORDINATES
# =============================================================================

def read_extent_from_group(group, key):
    key_lower = key.lower()

    for attr_name, raw in group.attrs.items():
        if str(attr_name).lower() == key_lower:
            return parse_float(raw)

    if isinstance(group, h5py.Group):
        for child_name, child in group.items():
            if (
                child_name.lower() == key_lower
                and isinstance(child, h5py.Dataset)
            ):
                return parse_float(child[()])

    return None


def find_extent_anywhere(h5, key):
    result = []
    key_lower = key.lower()

    def visitor(name, obj):
        if result:
            return

        for attr_name, raw in obj.attrs.items():
            if str(attr_name).lower() == key_lower:
                value = parse_float(raw)
                if value is not None:
                    result.append(value)
                    return

        if isinstance(obj, h5py.Dataset):
            if name.rsplit("/", 1)[-1].lower() == key_lower:
                try:
                    value = parse_float(obj[()])
                    if value is not None:
                        result.append(value)
                except Exception:
                    pass

    h5.visititems(visitor)
    return result[0] if result else None


def get_physical_extents(h5, verbose=True):
    keys = [
        "ExtMin0", "ExtMax0",
        "ExtMin1", "ExtMax1",
        "ExtMin2", "ExtMax2",
    ]

    values = {}

    if "DataSetInfo/Image" in h5:
        image = h5["DataSetInfo/Image"]
        for key in keys:
            v = read_extent_from_group(image, key)
            if v is not None:
                values[key] = v

    for key in keys:
        if key not in values:
            v = find_extent_anywhere(h5, key)
            if v is not None:
                values[key] = v

    missing = [key for key in keys if key not in values]
    if missing:
        raise RuntimeError(
            "Could not determine physical extents: "
            + ", ".join(missing)
        )

    extents = tuple(values[k] for k in keys)
    min_x, max_x, min_y, max_y, min_z, max_z = extents

    if not (
        max_x > min_x
        and max_y > min_y
        and max_z > min_z
    ):
        raise RuntimeError(
            f"Invalid physical extents: {extents}"
        )

    if verbose:
        print("Physical image extents:")
        print(f"  X: {min_x:.6f} .. {max_x:.6f} um")
        print(f"  Y: {min_y:.6f} .. {max_y:.6f} um")
        print(f"  Z: {min_z:.6f} .. {max_z:.6f} um")

    return extents


def normalize_xyz(xyz):
    xyz = np.asarray(xyz, dtype=np.float32)

    if xyz.size == 0:
        return np.empty((0, 3), dtype=np.float32)

    if xyz.ndim != 2 or xyz.shape[1] != 3:
        raise ValueError(
            f"Expected physical XYZ with shape (N,3), got {xyz.shape}"
        )

    return xyz


def validate_positions_inside_image(h5, predictions):
    min_x, max_x, min_y, max_y, min_z, max_z = get_physical_extents(
        h5,
        verbose=False,
    )

    for cfg in PREDICTED_GROUPS:
        xyz = normalize_xyz(
            predictions.get(cfg["name"], np.empty((0, 3), np.float32))
        )

        if len(xyz) == 0:
            continue

        inside = (
            (xyz[:, 0] >= min_x)
            & (xyz[:, 0] <= max_x)
            & (xyz[:, 1] >= min_y)
            & (xyz[:, 1] <= max_y)
            & (xyz[:, 2] >= min_z)
            & (xyz[:, 2] <= max_z)
        )

        if not np.all(inside):
            bad = np.flatnonzero(~inside)
            raise ValueError(
                f"{cfg['name']}: spots outside image bounds: "
                f"{bad.tolist()}"
            )


def get_level0_shape_zyx(h5):
    path = "DataSet/ResolutionLevel 0/TimePoint 0"
    if path not in h5:
        raise RuntimeError(f"Missing {path}")

    tp = h5[path]
    channels = sorted(k for k in tp if k.startswith("Channel"))
    if not channels:
        raise RuntimeError("No channels at ResolutionLevel 0 / TimePoint 0")

    return tuple(tp[channels[0]]["Data"].shape)


def voxel_zyx_to_physical_xyz(h5, voxel_zyx):
    """
    Future model helper:
        model voxel [z, y, x] -> Imaris physical [x_um, y_um, z_um]
    """
    arr = np.asarray(voxel_zyx, dtype=np.float64)

    if arr.size == 0:
        return np.empty((0, 3), np.float32)

    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(
            f"Expected voxel coordinates (N,3), got {arr.shape}"
        )

    nz, ny, nx = get_level0_shape_zyx(h5)
    min_x, max_x, min_y, max_y, min_z, max_z = get_physical_extents(
        h5,
        verbose=False,
    )

    z = arr[:, 0]
    y = arr[:, 1]
    x = arr[:, 2]

    x_um = min_x + ((x + 0.5) / nx) * (max_x - min_x)
    y_um = min_y + ((y + 0.5) / ny) * (max_y - min_y)
    z_um = min_z + ((z + 0.5) / nz) * (max_z - min_z)

    return np.column_stack([x_um, y_um, z_um]).astype(np.float32)


# =============================================================================
# SERIALIZED Scene/Data + Scene8/Data XML
# =============================================================================

POINTS_VIEWER_RE = re.compile(
    r"\s*<bpPointsViewer>.*?</bpPointsViewer>",
    flags=re.S,
)


def read_scene_xml(dataset):
    if not isinstance(dataset, h5py.Dataset):
        raise TypeError(
            f"Expected serialized scene Data to be an h5py.Dataset, "
            f"got {type(dataset).__name__} at {dataset.name}."
        )
    if dataset.shape != (1,):
        raise ValueError(
            f"Expected serialized scene Data shape (1,), got "
            f"{dataset.shape} at {dataset.name}."
        )

    raw = np.asarray(
        dataset[0],
        dtype=np.int8,
    ).astype(np.uint8).tobytes()

    return raw.decode("utf-8", errors="ignore")


def write_scene_xml(dataset, xml):
    raw = np.frombuffer(
        xml.encode("utf-8"),
        dtype=np.uint8,
    ).view(np.int8)

    dataset[0] = raw


def extract_points_viewers(xml):
    return [
        match.group(0).strip()
        for match in POINTS_VIEWER_RE.finditer(xml)
    ]


def strip_points_viewers(xml):
    return POINTS_VIEWER_RE.sub("", xml)


def copy_scene_data_if_missing(
    target_scene,
    donor_scene,
):
    """
    Return a native-writable serialized scene Data DATASET.

    IMPORTANT IMARIS PERSISTENCE DETAIL
    -----------------------------------
    Imaris-created files store Scene/Data and Scene8/Data as a one-element,
    variable-length int8 dataset that is CHUNKED and RESIZABLE:

        shape    = (1,)
        maxshape = (None,)
        chunks   = (1,)

    Earlier versions of this writer accepted any shape-(1,) dataset, or created
    a fixed/contiguous one. Such files display scripted Spot groups correctly,
    but Imaris can fail to persist the bpPointsViewer XML for NEW manually
    created Spot groups on Save + Close.

    This function therefore normalizes the storage layout to native Imaris
    semantics while preserving the target's existing scene XML whenever it can
    be read.
    """
    if (
        "Data" not in donor_scene
        or not isinstance(
            donor_scene["Data"],
            h5py.Dataset,
        )
    ):
        raise RuntimeError(
            f"Schema donor {donor_scene.name}/Data is not a valid Dataset."
        )

    donor_ds = donor_scene["Data"]

    # Preserve the target's existing serialized scene XML when readable.
    preserved_xml = None

    if "Data" in target_scene:
        existing = target_scene["Data"]

        if isinstance(
            existing,
            h5py.Dataset,
        ):
            try:
                if existing.shape == (1,):
                    preserved_xml = read_scene_xml(
                        existing
                    )
            except Exception:
                preserved_xml = None

        # If it is already native-writable, keep it unchanged.
        if (
            isinstance(
                existing,
                h5py.Dataset,
            )
            and existing.shape == (1,)
            and existing.maxshape is not None
            and existing.maxshape[0] is None
            and existing.chunks == (1,)
        ):
            return existing

        print(
            f"  Rebuilding {target_scene.name}/Data in native Imaris "
            "resizable/chunked layout."
        )

        del target_scene["Data"]

    if preserved_xml is None:
        # Use the target-independent donor scene as the safe structural base,
        # but strip its Points viewers; they are installed separately below.
        preserved_xml = strip_points_viewers(
            read_scene_xml(
                donor_ds
            )
        )

    raw = np.frombuffer(
        preserved_xml.encode(
            "utf-8"
        ),
        dtype=np.uint8,
    ).view(
        np.int8
    )

    # Match the donor's vlen element dtype, but explicitly guarantee the
    # resizable/chunked storage properties used by native Imaris files.
    dtype = donor_ds.dtype

    ds = target_scene.create_dataset(
        "Data",
        shape=(1,),
        maxshape=(None,),
        chunks=(1,),
        dtype=dtype,
    )

    ds[0] = raw

    return ds



def set_points_group_identity(points_group, display_name, point_id):
    encoded = str(display_name).encode("utf-8")
    if "Name" in points_group.attrs:
        del points_group.attrs["Name"]
    points_group.attrs.create(
        "Name",
        np.asarray([encoded], dtype=f"S{max(1, len(encoded))}"),
    )
    points_group.attrs["Id"] = np.uint64(int(point_id))


def clone_rotation_viewer_block(viewer_blocks, display_name):
    rot_cfg = next(cfg for cfg in MANUAL_EMPTY_GROUPS if cfg["name"] == "rot")
    source_id = int(rot_cfg["clone_from_id"])
    source_token = f'<bpPointsId Value="{source_id}"/>'
    block = next((b for b in viewer_blocks if source_token in b), None)
    if block is None:
        raise RuntimeError("Could not find donor Points viewer to clone for rotation group.")

    ids = []
    for b in viewer_blocks:
        m = re.search(
            r"<bpSurfaceComponent>\s*<name>.*?</name>\s*<id>(\d+)</id>",
            b,
            flags=re.S,
        )
        if m:
            ids.append(int(m.group(1)))
    new_component_id = max(ids) + 1 if ids else 999

    block = re.sub(
        r"(<bpSurfaceComponent>\s*<name>)(.*?)(</name>)",
        lambda m: m.group(1) + str(display_name) + m.group(3),
        block,
        count=1,
        flags=re.S,
    )
    block = re.sub(
        r"(<bpSurfaceComponent>\s*<name>.*?</name>\s*<id>)(\d+)(</id>)",
        lambda m: m.group(1) + str(new_component_id) + m.group(3),
        block,
        count=1,
        flags=re.S,
    )
    block = block.replace(
        source_token,
        f'<bpPointsId Value="{int(rot_cfg["id"])}"/>',
        1,
    )
    return block


def rename_points_viewer(scene_data, point_id, display_name):
    xml = read_scene_xml(scene_data)
    token = f'<bpPointsId Value="{int(point_id)}"/>'
    pos = xml.find(token)
    if pos < 0:
        raise RuntimeError(f"Missing viewer for rotation point id {point_id}.")
    start = xml.rfind("<bpPointsViewer>", 0, pos)
    end = xml.find("</bpPointsViewer>", pos)
    if start < 0 or end < 0:
        raise RuntimeError("Could not isolate rotation bpPointsViewer block.")
    end += len("</bpPointsViewer>")
    block = xml[start:end]
    block = re.sub(
        r"(<bpSurfaceComponent>\s*<name>)(.*?)(</name>)",
        lambda m: m.group(1) + str(display_name) + m.group(3),
        block,
        count=1,
        flags=re.S,
    )
    write_scene_xml(scene_data, xml[:start] + block + xml[end:])


def install_points_viewers(
    target_scene,
    donor_scene,
    rotation_group_name=None,
):
    """
    Reference-writer behavior from test_ims_scene_edit.py.

    Copy the donor's exact bpPointsViewer blocks. Do not dynamically renumber
    them and do not involve Scene8/Tree.
    """
    target_data = copy_scene_data_if_missing(
        target_scene,
        donor_scene,
    )

    target_xml = strip_points_viewers(
        read_scene_xml(target_data)
    )

    donor_xml = read_scene_xml(
        donor_scene["Data"]
    )

    viewer_blocks = extract_points_viewers(
        donor_xml
    )

    if len(viewer_blocks) == len(GROUPS) - 1:
        viewer_blocks = list(viewer_blocks)
        viewer_blocks.append(
            clone_rotation_viewer_block(
                viewer_blocks,
                rotation_group_name or "rotat=NA",
            )
        )
    elif len(viewer_blocks) != len(GROUPS):
        raise RuntimeError(
            f"Expected {len(GROUPS) - 1} or {len(GROUPS)} bpPointsViewer blocks "
            f"in schema donor, found {len(viewer_blocks)}"
        )

    payload = (
        "\n"
        + "\n".join(viewer_blocks)
        + "\n"
    )

    anchor = "</bpVolumeRenderer>"
    pos = target_xml.find(anchor)

    if pos >= 0:
        pos += len(anchor)
        target_xml = (
            target_xml[:pos]
            + payload
            + target_xml[pos:]
        )
    else:
        # Same fallback used by the known-good reference script.
        target_xml = donor_xml

    write_scene_xml(
        target_data,
        target_xml,
    )



def get_target_time_strings(h5):
    """
    Return the target image's own absolute time in the two text formats used
    by Imaris Points metadata.

    A schema donor may have been acquired on another day. Copying its absolute
    point timestamp unchanged can put all Spots millions of seconds away from
    the image's time point.
    """
    if "DataSetInfo/TimeInfo" not in h5:
        raise RuntimeError(
            "Missing DataSetInfo/TimeInfo; cannot synchronize Spot time."
        )

    time_info = h5[
        "DataSetInfo/TimeInfo"
    ]

    raw = time_info.attrs.get(
        "TimePoint1"
    )

    if raw is None:
        candidates = sorted(
            key
            for key in time_info.attrs
            if str(key).startswith(
                "TimePoint"
            )
        )

        if not candidates:
            raise RuntimeError(
                "No TimePoint* metadata found in DataSetInfo/TimeInfo."
            )

        raw = time_info.attrs[
            candidates[0]
        ]

    raw_text = decode_h5_text(
        raw
    ).strip()

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2} "
        r"\d{2}:\d{2}:\d{2})"
        r"(?:\.(\d+))?",
        raw_text,
    )

    if match is None:
        raise RuntimeError(
            f"Unexpected target TimePoint format: {raw_text!r}"
        )

    base = match.group(1)
    fraction = match.group(2) or ""

    milliseconds = (
        fraction + "000"
    )[:3]

    nanoseconds = (
        fraction + "000000000"
    )[:9]

    return (
        f"{base}.{milliseconds}",
        f"{base}.{nanoseconds}",
    )


def synchronize_points_time_metadata(
    target,
):
    """
    Replace donor absolute timestamps in all copied Point groups with the target
    image's own acquisition timestamp.
    """
    scene_time, scene8_time = get_target_time_strings(
        target
    )

    print(
        "Synchronizing Spot time metadata to target image:"
    )
    print(
        f"  Scene TimeInfos : {scene_time}"
    )
    print(
        f"  Scene8 TimeBegin: {scene8_time}"
    )

    for cfg in GROUPS:
        container = cfg[
            "container"
        ]

        scene_group = target[
            f"Scene/Content/{container}"
        ]

        if "TimeInfos" in scene_group:
            dtype = scene_group[
                "TimeInfos"
            ].dtype

            del scene_group[
                "TimeInfos"
            ]

            scene_group.create_dataset(
                "TimeInfos",
                data=np.asarray(
                    [
                        scene_time.encode(
                            "utf-8"
                        )
                    ],
                    dtype=dtype,
                ),
                dtype=dtype,
            )

        scene8_group = target[
            f"Scene8/Content/{container}"
        ]

        if "TimeBegin" in scene8_group:
            dtype = scene8_group[
                "TimeBegin"
            ].dtype

            values = np.zeros(
                1,
                dtype=dtype,
            )

            names = dtype.names or ()

            if "ID" in names:
                values[
                    "ID"
                ] = 0

            if "ObjectTimeBegin" in names:
                values[
                    "ObjectTimeBegin"
                ] = scene8_time.encode(
                    "utf-8"
                )

            del scene8_group[
                "TimeBegin"
            ]

            scene8_group.create_dataset(
                "TimeBegin",
                data=values,
                dtype=dtype,
            )


def update_scene_points_group(
    group,
    xyz,
    radius_um,
):
    xyz = normalize_xyz(xyz)
    n = len(xyz)

    xyzr = np.column_stack([
        xyz,
        np.full(n, radius_um, dtype=np.float32),
    ]).astype(np.float32)

    replace_dataset(
        group,
        "CoordsXYZR",
        xyzr,
        dtype=np.float32,
    )

    replace_dataset(
        group,
        "Time",
        np.zeros((n, 1), dtype=np.int64),
        dtype=np.int64,
    )

    # TimeInfos is synchronized to the target image after schema copying.
    return group



# =============================================================================
# Scene8/Content/PointsX
# =============================================================================

def regenerate_statistics(
    group,
    xyz,
    radius_um,
):
    """
    Rebuild StatisticsValue for arbitrary N while preserving the donor's
    StatisticsType/Factor/Category schema.

    The rendering does not depend on these values, but keeping the table
    internally consistent avoids stale object IDs/counts.
    """
    xyz = normalize_xyz(xyz)
    n = len(xyz)

    if "StatisticsType" not in group:
        return

    stat_type = group["StatisticsType"][()]
    stat_dtype = group["StatisticsValue"].dtype

    name_by_id = {
        int(row["ID"]):
        row["Name"].decode("utf-8", errors="ignore").rstrip("\x00")
        for row in stat_type
    }

    # In the supplied manual scene there are two group/time-level rows:
    # Total Number of Spots + Number of Spots per Time Point.
    rows = []

    for stat_id, name in name_by_id.items():
        if name == "Total Number of Spots":
            rows.append((-1, -1, stat_id, float(n)))
            continue

        if name == "Number of Spots per Time Point":
            rows.append((0, -1, stat_id, float(n)))
            continue

        for object_id in range(n):
            value = 0.0

            if name == "Position X":
                value = float(xyz[object_id, 0])
            elif name == "Position Y":
                value = float(xyz[object_id, 1])
            elif name == "Position Z":
                value = float(xyz[object_id, 2])
            elif name in ("Diameter X", "Diameter Y", "Diameter Z"):
                value = float(2.0 * radius_um)
            elif name == "Area":
                # Manual radius 0.5 -> area pi.
                value = float(4.0 * math.pi * radius_um ** 2)
            elif name == "Volume":
                value = float((4.0 / 3.0) * math.pi * radius_um ** 3)

            rows.append((0, object_id, stat_id, value))

    values = np.array(rows, dtype=stat_dtype)

    replace_dataset(
        group,
        "StatisticsValue",
        values,
        dtype=stat_dtype,
    )

    if "StatisticsValueTimeOffset" in group:
        offset_dtype = group["StatisticsValueTimeOffset"].dtype

        offsets = np.zeros(2, dtype=offset_dtype)
        offsets[0] = (-1, 0, 1)
        offsets[1] = (0, 1, len(values))

        replace_dataset(
            group,
            "StatisticsValueTimeOffset",
            offsets,
            dtype=offset_dtype,
        )


def update_scene8_points_group(
    group,
    xyz,
    radius_um,
):
    xyz = normalize_xyz(xyz)
    n = len(xyz)

    spot_dtype = group["Spot"].dtype
    spots = np.zeros(n, dtype=spot_dtype)

    if n:
        spots["ID"] = np.arange(n, dtype=np.int64)
        spots["PositionX"] = xyz[:, 0]
        spots["PositionY"] = xyz[:, 1]
        spots["PositionZ"] = xyz[:, 2]
        spots["Radius"] = np.float32(radius_um)

    replace_dataset(
        group,
        "Spot",
        spots,
        dtype=spot_dtype,
    )

    offset_dtype = group["SpotTimeOffset"].dtype
    if n:
        spot_offset = np.zeros(1, dtype=offset_dtype)
        spot_offset[0] = (0, 0, n)
    else:
        spot_offset = np.zeros(0, dtype=offset_dtype)

    replace_dataset(
        group,
        "SpotTimeOffset",
        spot_offset,
        dtype=offset_dtype,
    )

    # Imaris creates one track-helper row per manual spot in this scene.
    for track_name in (
        "TrackSegment0",
        "TrackSegment0_Focus",
    ):
        if track_name in group:
            dtype = group[track_name].dtype
            tracks = np.zeros(n, dtype=dtype)

            if n:
                tracks["ID"] = np.arange(n, dtype=np.int64)
                tracks["FirstObjectId"] = np.arange(n, dtype=np.int64)
                tracks["Position"] = np.arange(n, dtype=np.float64)

            replace_dataset(
                group,
                track_name,
                tracks,
                dtype=dtype,
            )

    regenerate_statistics(
        group,
        xyz,
        radius_um,
    )




# =============================================================================
# MANUAL DRAWING / EDIT MODE METADATA
# =============================================================================

def set_manual_drawing_metadata(points_group):
    """
    Match the creation-state flag used by the donor's manual ce/bo/si/to
    groups, while preserving all predicted Spots and all other object metadata.

    In the supplied donor the relevant creation-parameter difference is:
        mEnableShortestDistance="false"
    instead of:
        mEnableShortestDistance="true"

    Imaris stores CreationParameters twice in Scene8, as both an attribute
    and a dataset, so both representations are updated.
    """
    old_token = b'mEnableShortestDistance="true"'
    new_token = b'mEnableShortestDistance="false"'

    # Group-level CreationParameters attribute.
    if "CreationParameters" in points_group.attrs:
        raw_attr = points_group.attrs["CreationParameters"]

        values = (
            list(raw_attr)
            if isinstance(raw_attr, np.ndarray)
            else [raw_attr]
        )

        converted = []
        for value in values:
            if isinstance(value, str):
                value = value.encode("utf-8")
            converted.append(
                bytes(value).replace(
                    old_token,
                    new_token,
                )
            )

        max_len = max(
            len(v)
            for v in converted
        )

        del points_group.attrs["CreationParameters"]
        points_group.attrs.create(
            "CreationParameters",
            np.asarray(
                converted,
                dtype=f"S{max_len}",
            ),
        )

    # Matching CreationParameters dataset.
    if "CreationParameters" in points_group:
        ds = points_group["CreationParameters"]
        raw_ds = ds[()]

        values = (
            list(raw_ds)
            if isinstance(raw_ds, np.ndarray)
            else [raw_ds]
        )

        converted = []
        for value in values:
            if isinstance(value, str):
                value = value.encode("utf-8")
            converted.append(
                bytes(value).replace(
                    old_token,
                    new_token,
                )
            )

        max_len = max(
            len(v)
            for v in converted
        )

        del points_group["CreationParameters"]
        points_group.create_dataset(
            "CreationParameters",
            data=np.asarray(
                converted,
                dtype=f"S{max_len}",
            ),
        )


def set_predicted_spot_rendering_in_scene_xml(
    scene_data_dataset,
):
    """
    Render g/b/r/405 as center points sized from the selected diameter.

    Imaris center points visually ignore Spot["Radius"] / CoordsXYZR and use
    ``mCenterPointSize`` in screen pixels instead. The physical micrometre
    radius remains stored in the Spot data and Diameter X/Y/Z statistics.
    """
    xml = read_scene_xml(
        scene_data_dataset
    )

    predicted_ids = {
        int(cfg["id"])
        for cfg in PREDICTED_GROUPS
    }

    changed = 0

    blocks = extract_points_viewers(
        xml
    )

    for original_block in blocks:
        id_match = re.search(
            r'<bpPointsId Value="(\d+)"/>',
            original_block,
        )

        if id_match is None:
            continue

        point_id = int(
            id_match.group(1)
        )

        if point_id not in predicted_ids:
            continue

        updated_block = original_block
        attributes = {
            "mStyle": "eCenterPoint",
            "mRadiusScale": "1",
            "mCenterPointSize": str(int(PREDICTED_CENTER_POINT_SIZE_PX)),
        }
        for attribute, value in attributes.items():
            updated_block, n_subs = re.subn(
                rf'{re.escape(attribute)}="[^"]*"',
                f'{attribute}="{value}"',
                updated_block,
                count=1,
            )
            if n_subs == 0:
                updated_block, n_subs = re.subn(
                    r'(<bpPointsProperties\b)',
                    rf'\1 {attribute}="{value}"',
                    updated_block,
                    count=1,
                )
            if n_subs != 1:
                raise RuntimeError(
                    f"Could not set {attribute} for Points ID {point_id}."
                )

        xml = xml.replace(
            original_block,
            updated_block,
            1,
        )

        changed += 1

    if changed != len(PREDICTED_GROUPS):
        raise RuntimeError(
            "Expected to update Spot viewer metadata for "
            f"{len(PREDICTED_GROUPS)} predicted viewers, changed {changed}."
        )

    write_scene_xml(
        scene_data_dataset,
        xml,
    )


def set_manual_drawing_metadata_in_scene_xml(
    scene_data_dataset,
    point_ids,
):
    """
    Apply the same manual-edit creation flag inside the serialized Scene XML
    for the requested Points viewer IDs only.
    """
    xml = read_scene_xml(
        scene_data_dataset
    )

    for point_id in point_ids:
        id_token = (
            f'<bpPointsId Value="{point_id}"/>'
        )

        id_pos = xml.find(
            id_token
        )

        if id_pos < 0:
            continue

        start = xml.rfind(
            "<bpPointsViewer>",
            0,
            id_pos,
        )

        end = xml.find(
            "</bpPointsViewer>",
            id_pos,
        )

        if start < 0 or end < 0:
            continue

        end += len(
            "</bpPointsViewer>"
        )

        block = xml[
            start:end
        ]

        block = block.replace(
            'mEnableShortestDistance="true"',
            'mEnableShortestDistance="false"',
        )

        xml = (
            xml[:start]
            + block
            + xml[end:]
        )

    write_scene_xml(
        scene_data_dataset,
        xml,
    )


# =============================================================================
# SCENE REGISTRATION COUNTERS
# =============================================================================

def ascii_uint8(text):
    """
    Imaris stores Scene/NumberOfElements as ASCII character codes in uint8.
    Example: '7' is stored as array([55], dtype=uint8).
    """
    return np.frombuffer(str(text).encode("ascii"), dtype=np.uint8).copy()


def imaris_text_attribute(text):
    """Encode text using the one-byte character-array format used by IMS."""
    return np.frombuffer(str(text).encode("ascii"), dtype="S1").copy()


def write_imaris_channel_display_ranges(h5, exposure_settings):
    """Store effective Neurodot black/white windows as Imaris ColorRange."""
    if exposure_settings is None:
        return {}

    # Local import avoids the imaris_io <-> image_io module cycle.

    channel_map = map_channels(h5, verbose=False)
    written = {}

    for logical_channel in CHANNEL_PROCESSING_ORDER:
        values = exposure_settings.get(logical_channel)
        channel_index = channel_map.get(logical_channel)
        if values is None or channel_index is None:
            continue

        black = float(values["black"])
        white = float(values["white"])
        if not math.isfinite(black) or not math.isfinite(white):
            raise ValueError(
                f"Non-finite display range for {logical_channel}: "
                f"{black}, {white}"
            )
        if white <= black:
            raise ValueError(
                f"Invalid display range for {logical_channel}: "
                f"black={black}, white={white}"
            )

        group_path = f"DataSetInfo/Channel {int(channel_index)}"
        if group_path not in h5:
            raise RuntimeError(
                f"Mapped Imaris display channel is missing: {group_path}"
            )

        range_text = f"{black:.6f} {white:.6f}"
        h5[group_path].attrs["ColorRange"] = imaris_text_attribute(range_text)
        written[logical_channel] = (int(channel_index), black, white)
        print(
            f"  Imaris display {logical_channel} -> Channel {channel_index}: "
            f"black={black:.3f}, white={white:.3f}"
        )

    return written


def validate_imaris_channel_display_ranges(h5, exposure_settings):
    """Read back and verify ColorRange values written for Imaris."""
    if exposure_settings is None:
        return


    channel_map = map_channels(h5, verbose=False)
    for logical_channel in CHANNEL_PROCESSING_ORDER:
        values = exposure_settings.get(logical_channel)
        channel_index = channel_map.get(logical_channel)
        if values is None or channel_index is None:
            continue

        group_path = f"DataSetInfo/Channel {int(channel_index)}"
        range_text = decode_h5_text(
            h5[group_path].attrs.get("ColorRange", "")
        ).strip()
        parts = range_text.split()
        if len(parts) != 2:
            raise AssertionError(
                f"Invalid ColorRange in {group_path}: {range_text!r}"
            )

        actual = np.asarray([float(parts[0]), float(parts[1])], dtype=np.float64)
        expected = np.asarray(
            [float(values["black"]), float(values["white"])],
            dtype=np.float64,
        )
        if not np.allclose(actual, expected, rtol=0.0, atol=1e-5):
            raise AssertionError(
                f"Imaris ColorRange mismatch for {logical_channel}: "
                f"written={actual.tolist()}, expected={expected.tolist()}"
            )
        print(
            f"  OK Imaris display {logical_channel} / Channel {channel_index}: "
            f"{actual[0]:.3f} .. {actual[1]:.3f}"
        )


def register_points_objects(scene):
    """
    Register the scripted Points groups using the native Imaris counter.

    Native manually-editable Imaris files use Content/NumberOfPoints.
    Do NOT synthesize Scene/NumberOfElements here: the functioning native files
    do not require that attribute, and a stale hard-coded value can conflict
    with objects that Imaris creates later.
    """
    content = scene[
        "Content"
    ]

    content.attrs[
        "NumberOfPoints"
    ] = np.uint64(
        len(
            GROUPS
        )
    )

    # Remove only the legacy value introduced by older versions of THIS script.
    # It was stored as ASCII uint8 for 3 base objects + len(GROUPS).
    if "NumberOfElements" in scene.attrs:
        raw = scene.attrs[
            "NumberOfElements"
        ]

        try:
            decoded = decode_h5_text(
                raw
            )

            legacy_expected = str(
                3 + len(
                    GROUPS
                )
            )

            if decoded == legacy_expected:
                del scene.attrs[
                    "NumberOfElements"
                ]

                print(
                    f"  Removed legacy scripted "
                    f"{scene.name}/NumberOfElements={decoded}"
                )
        except Exception:
            # Preserve unknown/native metadata rather than deleting it.
            pass




def reset_imaris_camera_to_image(h5):
    """Best-effort equivalent of an Imaris Fit/Reset for the saved Surpass view.

    Some source .ims files contain a Surpass camera position copied from a
    different dataset. The image itself is valid, but Imaris can therefore open
    looking into empty space until the user presses Reset/Fit. Recompute the
    camera from this file's physical extents and update only the Surpass camera
    fields in serialized Scene/Data and Scene8/Data.
    """
    # Imported locally to keep the Imaris writer independent of image reading
    # at module-import time while preserving the established geometry definition.

    geo = get_image_geometry(h5, verbose=False)
    cx = 0.5 * (float(geo["min_x"]) + float(geo["max_x"]))
    cy = 0.5 * (float(geo["min_y"]) + float(geo["max_y"]))
    cz = 0.5 * (float(geo["min_z"]) + float(geo["max_z"]))
    span_x = float(geo["max_x"] - geo["min_x"])
    span_y = float(geo["max_y"] - geo["min_y"])
    span = max(span_x, span_y, 1e-6)

    # Imaris' normal Surpass perspective camera uses a ~45 degree vertical FOV.
    height_angle = 0.78539816339
    focal = (0.5 * span / math.tan(0.5 * height_angle)) * 1.03
    position = (cx, cy, cz - focal)
    orientation = "(1.000, 0.000, 0.000, 3.142)"

    def replace_tag(xml, tag, value):
        pattern = rf"(<{re.escape(tag)}>).*?(</{re.escape(tag)}>)"
        return re.sub(pattern, rf"\g<1>{value}\g<2>", xml, count=1, flags=re.S)

    for scene_name in ("Scene", "Scene8"):
        path = f"{scene_name}/Data"
        if path not in h5 or not isinstance(h5[path], h5py.Dataset):
            continue
        try:
            xml = read_scene_xml(h5[path])
        except Exception:
            continue

        pos_text = f"({position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f})"
        focal_text = f"{focal:.3f}"

        for prefix in ("SurpassSoPerspectiveCamera", "SurpassSoOrthographicCamera"):
            xml = replace_tag(xml, prefix + "position", pos_text)
            xml = replace_tag(xml, prefix + "orientation", orientation)
            xml = replace_tag(xml, prefix + "focalDistance", focal_text)

        # A fitted orthographic view should span the whole XY field as well.
        xml = replace_tag(
            xml,
            "SurpassSoOrthographicCameraheight",
            f"{span * 1.03:.3f}",
        )
        write_scene_xml(h5[path], xml)

    print(
        "Reset Imaris saved camera to image centre: "
        f"({cx:.3f}, {cy:.3f}, {cz:.3f}) um; fit distance={focal:.3f} um"
    )


# =============================================================================
# MAIN WRITER
# =============================================================================

def populate_ims_scene(
    input_ims,
    schema_donor_ims,
    output_ims,
    predictions,
    rotation_group_name=None,
    display_exposure_settings=None,
):
    """
    Write Spots using the proven schema-donor strategy from
    test_ims_scene_edit.py.

    IMPORTANT:
      * Scene8/Tree is NOT created or modified.
      * donor PointsViewer blocks are copied exactly.
      * every copied Points group has its N-dependent datasets rewritten.
      * ce/bo/si/to are explicitly rewritten to zero spots so donor example
        coordinates cannot leak into the target file.
    """
    input_ims = Path(input_ims)
    schema_donor_ims = Path(schema_donor_ims)
    output_ims = Path(output_ims)

    if not input_ims.exists():
        raise FileNotFoundError(input_ims)

    if not schema_donor_ims.exists():
        raise FileNotFoundError(schema_donor_ims)

    output_ims.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if input_ims.resolve() != output_ims.resolve():
        shutil.copyfile(
            input_ims,
            output_ims,
        )

    predicted_names = {
        cfg["name"]
        for cfg in PREDICTED_GROUPS
    }

    with h5py.File(schema_donor_ims, "r") as donor, \
         h5py.File(output_ims, "r+") as target:

        print("\nWriting Imaris channel display ranges:")
        write_imaris_channel_display_ranges(
            target,
            display_exposure_settings,
        )

        validate_positions_inside_image(
            target,
            predictions,
        )

        # Reproduce the known-good Points schema in BOTH Scene layers.
        for scene_name in ("Scene", "Scene8"):
            if scene_name not in donor:
                raise RuntimeError(
                    f"Schema donor is missing {scene_name}"
                )

            if scene_name not in target:
                scene = target.create_group(scene_name)

                for key, value in donor[
                    scene_name
                ].attrs.items():
                    scene.attrs[key] = value
            else:
                scene = target[scene_name]

            if "Content" not in scene:
                content = scene.create_group(
                    "Content"
                )
            else:
                content = scene["Content"]

            donor_content = donor[
                f"{scene_name}/Content"
            ]

            for cfg in GROUPS:
                container = cfg["container"]
                source_container = cfg.get("clone_from_container", container)

                if source_container not in donor_content:
                    raise RuntimeError(
                        f"Schema donor is missing "
                        f"{scene_name}/Content/{source_container}"
                    )

                if container in content:
                    del content[container]

                copied_group = copy_group_between_files(
                    donor_content[source_container],
                    content,
                    container,
                )

                if cfg.get("dynamic_name"):
                    set_points_group_identity(
                        copied_group,
                        rotation_group_name or "rotat=NA",
                        cfg["id"],
                    )

            install_points_viewers(
                scene,
                donor[scene_name],
                rotation_group_name=rotation_group_name,
            )

            register_points_objects(
                scene
            )

        # Overwrite EVERY copied group's spot data.
        #
        # A schema donor often contains one manually-created example point per
        # group. If helper groups are merely copied and left untouched those
        # donor coordinates appear as isolated spots far outside the target
        # image. Explicitly set helper groups to N=0.
        empty_xyz = np.empty(
            (0, 3),
            dtype=np.float32,
        )

        for cfg in GROUPS:
            name = cfg["name"]
            container = cfg["container"]
            radius_um = float(
                cfg.get(
                    "radius_um",
                    0.5,
                )
            )

            if name in predictions:
                xyz = normalize_xyz(
                    predictions.get(
                        name,
                        empty_xyz,
                    )
                )
            else:
                xyz = empty_xyz.copy()

            update_scene_points_group(
                target[
                    f"Scene/Content/{container}"
                ],
                xyz,
                radius_um,
            )

            scene8_group = target[
                f"Scene8/Content/{container}"
            ]

            update_scene8_points_group(
                scene8_group,
                xyz,
                radius_um,
            )

            # Preserve manual drawing/edit metadata, but never donor positions.
            set_manual_drawing_metadata(
                scene8_group
            )

            print(
                f"{container} / {name}: "
                f"{len(xyz)} spots"
            )

        # The schema donor may have a different acquisition date. Without
        # this synchronization Imaris can put all Spots at a completely
        # different absolute time from the image.
        synchronize_points_time_metadata(
            target
        )

        if RESET_IMARIS_CAMERA_ON_EXPORT:
            reset_imaris_camera_to_image(target)

        # Keep predicted objects as center points, but synchronize their fixed
        # pixel width with the selected diameter's numeric value.
        for scene_name in ("Scene", "Scene8"):
            set_predicted_spot_rendering_in_scene_xml(
                target[
                    f"{scene_name}/Data"
                ]
            )

        # Apply edit-mode metadata in the serialized viewer blocks only.
        for scene_name in ("Scene", "Scene8"):
            set_manual_drawing_metadata_in_scene_xml(
                target[
                    f"{scene_name}/Data"
                ],
                [
                    cfg["id"]
                    for cfg in GROUPS
                ],
            )

        if rotation_group_name is not None:
            rot_cfg = next(cfg for cfg in MANUAL_EMPTY_GROUPS if cfg["name"] == "rot")
            for scene_name in ("Scene", "Scene8"):
                rename_points_viewer(
                    target[f"{scene_name}/Data"],
                    rot_cfg["id"],
                    rotation_group_name,
                )

        # Manual helper groups may now contain the one GUI-clicked landmark.
        # Their Scene and Scene8 counts must agree with the supplied prediction.
        for cfg in MANUAL_EMPTY_GROUPS:
            name = cfg[
                "name"
            ]
            container = cfg[
                "container"
            ]

            expected_xyz = normalize_xyz(
                predictions.get(
                    name,
                    empty_xyz,
                )
            )

            expected_n = len(
                expected_xyz
            )

            n_scene = target[
                f"Scene/Content/{container}/CoordsXYZR"
            ].shape[
                0
            ]

            n_scene8 = target[
                f"Scene8/Content/{container}/Spot"
            ].shape[
                0
            ]

            if (
                n_scene != expected_n
                or n_scene8 != expected_n
            ):
                raise RuntimeError(
                    f"Manual group count mismatch in {container}/{name}: "
                    f"expected={expected_n}, "
                    f"Scene={n_scene}, Scene8={n_scene8}"
                )

    print(
        "Manual helper groups: ce, bo, si, to plus empty rotation metadata group"
    )

    validate_output(
        output_ims,
        predictions,
        display_exposure_settings=display_exposure_settings,
    )

    return output_ims


# =============================================================================
# VALIDATION
# =============================================================================

def validate_output(
    output_ims,
    predictions,
    display_exposure_settings=None,
):
    print("\nValidating written file...")

    with h5py.File(
        output_ims,
        "r",
    ) as h5:

        validate_imaris_channel_display_ranges(
            h5,
            display_exposure_settings,
        )

        # Predicted groups: arbitrary N, and Scene + Scene8 must agree.
        for cfg in PREDICTED_GROUPS:
            name = cfg["name"]
            container = cfg["container"]

            xyz = normalize_xyz(
                predictions.get(
                    name,
                    np.empty(
                        (0, 3),
                        dtype=np.float32,
                    ),
                )
            )

            n = len(xyz)

            scene_coords = h5[
                f"Scene/Content/{container}/CoordsXYZR"
            ]

            scene8_spot = h5[
                f"Scene8/Content/{container}/Spot"
            ]

            if scene_coords.shape != (n, 4):
                raise AssertionError(
                    f"Scene {container}: "
                    f"{scene_coords.shape} != {(n, 4)}"
                )

            if scene8_spot.shape != (n,):
                raise AssertionError(
                    f"Scene8 {container}: "
                    f"{scene8_spot.shape} != {(n,)}"
                )

            if n:
                a = scene_coords[:, :3]

                b = np.column_stack([
                    scene8_spot["PositionX"],
                    scene8_spot["PositionY"],
                    scene8_spot["PositionZ"],
                ])

                if not np.allclose(
                    a,
                    b,
                ):
                    raise AssertionError(
                        f"{container}: Scene and Scene8 coordinates differ"
                    )

            print(
                f"  OK {container} / {name}: "
                f"{n} predicted spots"
            )

        # Manual groups: schema must exist and counts/coordinates must agree with
        # the GUI-click predictions (normally exactly one each).
        for cfg in MANUAL_EMPTY_GROUPS:
            name = cfg[
                "name"
            ]
            container = cfg[
                "container"
            ]

            expected_xyz = normalize_xyz(
                predictions.get(
                    name,
                    np.empty(
                        (
                            0,
                            3,
                        ),
                        dtype=np.float32,
                    ),
                )
            )

            n = len(
                expected_xyz
            )

            scene_coords = h5[
                f"Scene/Content/{container}/CoordsXYZR"
            ]

            scene8_spot = h5[
                f"Scene8/Content/{container}/Spot"
            ]

            if scene_coords.shape != (
                n,
                4,
            ):
                raise AssertionError(
                    f"{container}/{name}: Scene shape "
                    f"{scene_coords.shape} != {(n, 4)}"
                )

            if scene8_spot.shape != (
                n,
            ):
                raise AssertionError(
                    f"{container}/{name}: Scene8 shape "
                    f"{scene8_spot.shape} != {(n,)}"
                )

            if n:
                scene_xyz = scene_coords[
                    :,
                    :3
                ]

                scene8_xyz = np.column_stack(
                    [
                        scene8_spot[
                            "PositionX"
                        ],
                        scene8_spot[
                            "PositionY"
                        ],
                        scene8_spot[
                            "PositionZ"
                        ],
                    ]
                )

                if not np.allclose(
                    scene_xyz,
                    expected_xyz,
                ):
                    raise AssertionError(
                        f"{container}/{name}: Scene coordinates "
                        "do not match GUI landmark."
                    )

                if not np.allclose(
                    scene8_xyz,
                    expected_xyz,
                ):
                    raise AssertionError(
                        f"{container}/{name}: Scene8 coordinates "
                        "do not match GUI landmark."
                    )

            print(
                f"  OK {container} / {name}: "
                f"{n} manual GUI spot(s)"
            )


        expected_scene_time, expected_scene8_time = get_target_time_strings(
            h5
        )

        for cfg in GROUPS:
            container = cfg[
                "container"
            ]

            actual_scene_time = decode_h5_text(
                h5[
                    f"Scene/Content/{container}/TimeInfos"
                ][0]
            )

            actual_scene8_time = decode_h5_text(
                h5[
                    f"Scene8/Content/{container}/TimeBegin"
                ][0]["ObjectTimeBegin"]
            )

            if actual_scene_time != expected_scene_time:
                raise AssertionError(
                    f"{container}: Scene TimeInfos={actual_scene_time!r}, "
                    f"expected {expected_scene_time!r}"
                )

            if actual_scene8_time != expected_scene8_time:
                raise AssertionError(
                    f"{container}: Scene8 TimeBegin={actual_scene8_time!r}, "
                    f"expected {expected_scene8_time!r}"
                )

        print(
            "  OK all Points timestamps match target image"
        )

        print(
            "  Scene serialization will be checked for native "
            "resizable/chunked layout"
        )

        # Scene registration and serialized viewer registration.
        for scene_name in ("Scene", "Scene8"):
            scene = h5[scene_name]
            content = scene["Content"]

            number_of_points = int(
                content.attrs.get(
                    "NumberOfPoints",
                    -1,
                )
            )

            if number_of_points != len(GROUPS):
                raise AssertionError(
                    f"{scene_name}/Content NumberOfPoints="
                    f"{number_of_points}, expected {len(GROUPS)}"
                )

            scene_data = h5[
                f"{scene_name}/Data"
            ]

            if scene_data.shape != (1,):
                raise AssertionError(
                    f"{scene_name}/Data shape={scene_data.shape}, expected (1,)"
                )

            if (
                scene_data.maxshape is None
                or scene_data.maxshape[0] is not None
            ):
                raise AssertionError(
                    f"{scene_name}/Data is not resizable: "
                    f"maxshape={scene_data.maxshape}"
                )

            if scene_data.chunks != (1,):
                raise AssertionError(
                    f"{scene_name}/Data is not native chunked layout: "
                    f"chunks={scene_data.chunks}"
                )

            xml = read_scene_xml(
                scene_data
            )

            if xml.count(
                "<bpPointsViewer>"
            ) != len(GROUPS):
                raise AssertionError(
                    f"{scene_name}/Data does not contain "
                    f"{len(GROUPS)} PointsViewer objects"
                )

            for cfg in GROUPS:
                token = (
                    f'<bpPointsId Value="{cfg["id"]}"/>'
                )

                if token not in xml:
                    raise AssertionError(
                        f"{scene_name}/Data missing {token}"
                    )

            # Predicted viewers remain center points with a width synchronized
            # numerically to the selected physical Spot diameter.
            for cfg in PREDICTED_GROUPS:
                point_id = int(
                    cfg["id"]
                )

                id_token = (
                    f'<bpPointsId Value="{point_id}"/>'
                )

                id_pos = xml.find(
                    id_token
                )

                start = xml.rfind(
                    "<bpPointsViewer>",
                    0,
                    id_pos,
                )

                end = xml.find(
                    "</bpPointsViewer>",
                    id_pos,
                )

                if start < 0 or end < 0:
                    raise AssertionError(
                        f"{scene_name}: could not isolate viewer for {point_id}"
                    )

                viewer_block = xml[
                    start:
                    end + len("</bpPointsViewer>")
                ]

                expected_attributes = (
                    'mStyle="eCenterPoint"',
                    'mRadiusScale="1"',
                    (
                        f'mCenterPointSize="'
                        f'{int(PREDICTED_CENTER_POINT_SIZE_PX)}'
                        f'"'
                    ),
                )
                missing = [
                    attribute
                    for attribute in expected_attributes
                    if attribute not in viewer_block
                ]
                if missing:
                    raise AssertionError(
                        f"{scene_name}: Points ID {point_id} does not have "
                        f"viewer metadata {missing}"
                    )

            print(
                f"  OK {scene_name}: predicted Spots render as center points "
                f"({PREDICTED_CENTER_POINT_SIZE_PX}px; physical diameter "
                f"{PREDICTED_SPOT_DIAMETER_UM:g} um)"
            )

    print(
        "Validation passed."
    )


# =============================================================================
# DEMO
# =============================================================================


# ============================================================================
# BEGIN GENERATED MODULE: image_io.py
# ============================================================================

"""Resolution-safe Imaris image reading, channel mapping, and rotation helpers."""
# =============================================================================
# STEP-4 MODEL INFERENCE — MANUAL IMARIS-LIKE EXPOSURE WINDOW

#
# RESOLUTION-SAFE IMARIS GEOMETRY
# -------------------------------
# Imaris .ims HDF5 datasets may be padded beyond the logical image size.
# Example:
#     logical X/Y = 4003 x 3998
#     storage X/Y may be 4096 x 4096
#
# Cellpose coordinates MUST be generated on the logical image and then mapped
# to physical coordinates using the same logical dimensions.  Mixing storage
# dimensions with DataSetInfo/Image dimensions causes a position error that
# grows across the field of view.
#

def _read_imaris_logical_dimension(image_group, key):
    """Read logical X/Y/Z integer dimension from DataSetInfo/Image."""
    candidates = (
        key,
        key.upper(),
        key.lower(),
        f"Size{key.upper()}",
        f"size{key.upper()}",
    )

    for name in candidates:
        if name in image_group.attrs:
            value = parse_float(
                image_group.attrs[name]
            )
            if value is not None:
                value = int(round(float(value)))
                if value > 0:
                    return value

    for name in candidates:
        if name in image_group:
            obj = image_group[name]
            if isinstance(obj, h5py.Dataset):
                value = parse_float(
                    obj[()]
                )
                if value is not None:
                    value = int(round(float(value)))
                    if value > 0:
                        return value

    return None


def get_imaris_logical_shape_zyx(h5):
    """
    Return Imaris's logical (Z,Y,X) dimensions.

    Prefer DataSetInfo/Image X/Y/Z. Fall back to the HDF5 storage shape only
    when the logical metadata is genuinely unavailable.
    """
    storage_z, storage_y, storage_x = get_level0_shape_zyx(
        h5
    )

    if "DataSetInfo/Image" not in h5:
        print(
            "  [geometry warning] DataSetInfo/Image missing; "
            "falling back to storage dimensions."
        )
        return (
            int(storage_z),
            int(storage_y),
            int(storage_x),
        )

    image = h5[
        "DataSetInfo/Image"
    ]

    logical_x = _read_imaris_logical_dimension(
        image,
        "X",
    )
    logical_y = _read_imaris_logical_dimension(
        image,
        "Y",
    )
    logical_z = _read_imaris_logical_dimension(
        image,
        "Z",
    )

    if logical_x is None:
        logical_x = int(storage_x)

    if logical_y is None:
        logical_y = int(storage_y)

    if logical_z is None:
        logical_z = int(storage_z)

    # A logical dimension larger than the stored level-0 array cannot be
    # cropped safely.  Fail loudly rather than creating silently shifted spots.
    if (
        logical_x > storage_x
        or logical_y > storage_y
        or logical_z > storage_z
    ):
        raise RuntimeError(
            "Imaris logical dimensions exceed level-0 HDF5 storage shape: "
            f"logical (Z,Y,X)=({logical_z},{logical_y},{logical_x}), "
            f"storage (Z,Y,X)=({storage_z},{storage_y},{storage_x})."
        )

    return (
        int(logical_z),
        int(logical_y),
        int(logical_x),
    )


def crop_volume_to_imaris_logical_shape(
    volume_zyx,
    logical_shape_zyx,
):
    """
    Remove HDF5 padding from the high-index Z/Y/X edges.

    Imaris logical coordinates refer to this cropped region, not to the padded
    storage array.
    """
    logical_z, logical_y, logical_x = (
        int(v)
        for v in logical_shape_zyx
    )

    volume = np.asarray(
        volume_zyx
    )

    if volume.ndim != 3:
        raise ValueError(
            f"Expected ZYX volume, got shape {volume.shape}"
        )

    storage_z, storage_y, storage_x = volume.shape

    if (
        logical_z > storage_z
        or logical_y > storage_y
        or logical_x > storage_x
    ):
        raise RuntimeError(
            "Cannot crop to logical Imaris dimensions because they exceed "
            f"storage: logical={logical_shape_zyx}, storage={volume.shape}"
        )

    return volume[
        :logical_z,
        :logical_y,
        :logical_x,
    ]


# Override the earlier geometry helper for inference WITHOUT touching the
# writer section above.  Python resolves this later definition at runtime.
def first_manual_landmark_key():
    return next(iter(MANUAL_GUI_LANDMARKS))

def normalize_rotation_to_ccw_only_convention(rotation_deg):
    """Return rotation in the project's stored CCW convention.

    The stored value is the amount of COUNTERCLOCKWISE rotation still needed to
    make the anatomical bottom->top midline vertical, encoded as a non-positive
    number. Examples:

        0° CCW  ->    0
        5° CCW  ->   -5
        30° CCW ->  -30
        180° CCW -> -180

    This intentionally replaces the old wrapped style where +5° CCW became
    -355. The user-facing value should reflect the intuitive small CCW amount.
    """
    if rotation_deg is None:
        return None
    value = float(rotation_deg) % 360.0
    if abs(value) < 0.005 or abs(value - 360.0) < 0.005:
        return 0.0
    return -value

def compute_counterclockwise_rotation_to_vertical_deg(landmarks_yx):
    """Return stored CCW rotation needed to orient bottom -> top vertically upward.

    The two clicks are directional:
        rot_bottom = anatomical bottom of the section midline
        rot_top    = anatomical top of the section midline

    This preserves orientation. Therefore an upside-down image is NOT treated
    as already straight: if bottom->top points downward on screen, the required
    correction is still ~180 degrees.

    Returned value convention:
        small CCW correction -> small negative number
        e.g. +7.6° geometric CCW becomes -7.6.
    """
    if not all(k in landmarks_yx for k in ROTATION_LANDMARK_KEYS):
        return None

    y_bottom, x_bottom = map(float, landmarks_yx['rot_bottom'])
    y_top, x_top = map(float, landmarks_yx['rot_top'])

    dx = x_top - x_bottom
    dy_image = y_top - y_bottom

    if abs(dx) < 1e-12 and abs(dy_image) < 1e-12:
        return 0.0

    dy_cartesian = -dy_image
    current_angle_deg = float(np.degrees(np.arctan2(dy_cartesian, dx)))

    # Desired bottom->top direction is vertically upward = +90°.
    geometric_ccw_deg = (90.0 - current_angle_deg) % 360.0
    if abs(geometric_ccw_deg) < 0.005 or abs(geometric_ccw_deg - 360.0) < 0.005:
        geometric_ccw_deg = 0.0

    return normalize_rotation_to_ccw_only_convention(geometric_ccw_deg)

def format_rotation_group_name(rotation_ccw_deg):
    if rotation_ccw_deg is None:
        return "rotat=NA"
    # rotation_ccw_deg is already in the stored project convention
    # (for example -7.60 means rotate 7.60 degrees counterclockwise).
    value = float(rotation_ccw_deg)
    if abs(value) < 0.005:
        value = 0.0
    return f"rotat={value:.2f}"


# =============================================================================
# CHANNEL MAPPING / IMAGE GEOMETRY
# =============================================================================

def logical_channel_from_emission_wavelength(wavelength_nm):
    """Map a finite emission wavelength into one strict Neurodot band."""
    wl = float(wavelength_nm)

    if not math.isfinite(wl):
        return None

    for target in ("405", "g", "r", "b"):
        low, high = CHANNEL_WAVELENGTH_BANDS_NM[target]

        if low is not None and wl < float(low):
            continue
        if high is not None and wl >= float(high):
            continue

        return target

    # With the open-ended first/last bands this should be unreachable for any
    # finite wavelength, but keep a defensive fallback.
    return None


def map_channels(h5, verbose=True):
    """Resolve g/r/b/405 using strict emission-wavelength bands.

    Priority:
      1. If a usable emission/wavelength value exists, map ONLY by the explicit
         CHANNEL_WAVELENGTH_BANDS_NM intervals.
      2. If wavelength metadata is absent/unparseable, fall back to an exact
         configured channel-name alias.

    The old first-digit wavelength shortcut and nearest-within-35-nm fallback
    are deliberately not used because they can leave valid far-red channels
    unmatched or classify unusual wavelengths unexpectedly.
    """
    mapping = {}
    ds_info = h5.get("DataSetInfo")

    if ds_info is None:
        raise RuntimeError("DataSetInfo is missing.")

    if verbose:
        print("\n--- Mapping Channels ---")
        print(
            "  Strict wavelength bands: "
            "405 <482 nm; g 482-<551 nm; "
            "r 551-<641 nm; b >=641 nm"
        )

    for key in ds_info.keys():
        if not key.startswith("Channel"):
            continue

        digits = "".join(c for c in key if c.isdigit())
        if not digits:
            continue

        ch_idx = int(digits)
        grp = ds_info[key]
        raw_name = decode_h5_text(
            grp.attrs.get("Name", "")
        ).strip().lower()

        raw_wl = ""
        for attr_name, raw_value in grp.attrs.items():
            if "emission" in str(attr_name).lower():
                raw_wl = decode_h5_text(raw_value)
                break

        if not raw_wl:
            for attr_name, raw_value in grp.attrs.items():
                if "wavelength" in str(attr_name).lower():
                    raw_wl = decode_h5_text(raw_value)
                    break

        matched = None
        match_reason = None

        # Wavelength is authoritative whenever it can be parsed.
        wl = parse_float(raw_wl) if raw_wl else None
        if wl is not None and math.isfinite(float(wl)):
            matched = logical_channel_from_emission_wavelength(wl)
            if matched is not None:
                match_reason = f"wavelength {float(wl):.2f} nm"

        # Only fall back to exact name aliases when wavelength metadata is not
        # usable. Do not let a channel name override a valid wavelength.
        if matched is None and wl is None:
            for target, cfg in TARGET_CONFIG.items():
                if raw_name in cfg["aliases"]:
                    matched = target
                    match_reason = f"name alias {raw_name!r}"
                    break

        if matched is None:
            if verbose:
                print(
                    f"  Channel {ch_idx} (Name={raw_name!r}, "
                    f"Emission={raw_wl!r}) -> UNMAPPED"
                )
            continue

        if matched in mapping:
            if verbose:
                print(
                    f"  Channel {ch_idx} (Name={raw_name!r}, "
                    f"Emission={raw_wl!r}) also maps to {matched!r} "
                    f"via {match_reason}; keeping earlier Channel "
                    f"{mapping[matched]}."
                )
            continue

        mapping[matched] = ch_idx

        if verbose:
            print(
                f"  Channel {ch_idx} (Name={raw_name!r}, "
                f"Emission={raw_wl!r}) -> {matched!r} "
                f"via {match_reason}"
            )

    return mapping


def get_image_geometry(h5, verbose=True):
    """
    ACTIVE resolution-safe geometry.

    IMPORTANT:
    Cellpose runs on the LOGICAL Imaris image after padded HDF5 edges are
    removed. Therefore pixel -> physical conversion MUST use those same
    logical X/Y/Z dimensions, never the padded storage dimensions.
    """
    storage_z, storage_y, storage_x = get_level0_shape_zyx(h5)

    logical_z, logical_y, logical_x = get_imaris_logical_shape_zyx(
        h5
    )

    min_x, max_x, min_y, max_y, min_z, max_z = get_physical_extents(
        h5,
        verbose=False,
    )

    geo = {
        "nx": int(logical_x),
        "ny": int(logical_y),
        "nz": int(logical_z),

        "storage_nx": int(storage_x),
        "storage_ny": int(storage_y),
        "storage_nz": int(storage_z),

        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
        "min_z": min_z,
        "max_z": max_z,

        "vx": (max_x - min_x) / float(logical_x),
        "vy": (max_y - min_y) / float(logical_y),
        "vz": (max_z - min_z) / float(logical_z),
    }

    if verbose:
        print("\n--- Image Geometry ---")
        print(
            "  logical (Z,Y,X): "
            f"({logical_z}, {logical_y}, {logical_x})"
        )
        print(
            "  HDF5 storage (Z,Y,X): "
            f"({storage_z}, {storage_y}, {storage_x})"
        )

        if (
            int(storage_z),
            int(storage_y),
            int(storage_x),
        ) != (
            int(logical_z),
            int(logical_y),
            int(logical_x),
        ):
            print(
                "  HDF5 padding detected: YES"
            )
            print(
                "  Coordinate conversion: LOGICAL dimensions "
                "(same domain as Cellpose)"
            )
        else:
            print(
                "  HDF5 padding detected: no"
            )

        print(
            f"  X: {min_x:.6f} .. {max_x:.6f} um  "
            f"vx={geo['vx']:.6f}"
        )
        print(
            f"  Y: {min_y:.6f} .. {max_y:.6f} um  "
            f"vy={geo['vy']:.6f}"
        )
        print(
            f"  Z: {min_z:.6f} .. {max_z:.6f} um  "
            f"vz={geo['vz']:.6f}"
        )

    return geo


def read_channel_volume_and_mip(h5, channel_index):
    """
    Read one level-0 channel and remove any HDF5 padding before returning it.
    The GUI preview, Test Cellpose, and batch inference therefore all operate
    in exactly the same logical Imaris pixel coordinate system.
    """
    dset_path = (
        "DataSet/ResolutionLevel 0/TimePoint 0/"
        f"Channel {int(channel_index)}/Data"
    )

    if dset_path not in h5:
        raise RuntimeError(
            f"Missing {dset_path}"
        )

    logical_shape = get_imaris_logical_shape_zyx(
        h5
    )

    volume = np.asarray(
        h5[dset_path][:]
    )

    storage_shape = tuple(
        volume.shape
    )

    volume = crop_volume_to_imaris_logical_shape(
        volume,
        logical_shape,
    )

    if tuple(volume.shape) != storage_shape:
        print(
            "  Cropped padded HDF5 channel volume: "
            f"{storage_shape} -> {tuple(volume.shape)}"
        )

    mip = np.max(
        volume,
        axis=0,
    )

    return volume, mip


def read_mip_for_file_channel(ims_path, logical_channel):
    """Read the exact logical level-0 MIP using a fast bulk HDF5 read.

    This GUI helper intentionally favors throughput over minimal RAM use. On a
    high-memory workstation, reading the logical 3D channel in one operation and
    reducing it with NumPy is substantially faster than issuing one HDF5 read per
    Z plane. The function is called from background worker threads, so the Tk GUI
    remains responsive while the data are loaded.
    """
    with h5py.File(ims_path, "r") as h5:
        mapping = map_channels(h5, verbose=False)
        if logical_channel not in mapping:
            return None

        channel_index = int(mapping[logical_channel])
        dset_path = (
            "DataSet/ResolutionLevel 0/TimePoint 0/"
            f"Channel {channel_index}/Data"
        )

        if dset_path not in h5:
            raise RuntimeError(f"Missing {dset_path}")

        logical_z, logical_y, logical_x = get_imaris_logical_shape_zyx(h5)
        dset = h5[dset_path]

        if logical_z <= 0 or logical_y <= 0 or logical_x <= 0:
            raise RuntimeError(
                f"Invalid logical Imaris dimensions: "
                f"{(logical_z, logical_y, logical_x)}"
            )

        # Read only the logical (unpadded) part of the level-0 channel.
        volume = np.asarray(
            dset[
                :int(logical_z),
                :int(logical_y),
                :int(logical_x),
            ]
        )

        mip = np.max(volume, axis=0)
        return np.asarray(mip)


def _choose_qc_resolution_level(level_shapes_zyx, logical_shape_zyx, target_size):
    """Choose the smallest Imaris pyramid level that remains at least target size."""
    if not level_shapes_zyx:
        raise RuntimeError("No Imaris resolution levels are available.")

    target_size = max(1, int(target_size))
    level0_shape = level_shapes_zyx[min(level_shapes_zyx)]
    logical_z0, logical_y0, logical_x0 = (int(value) for value in logical_shape_zyx)
    storage_z0, storage_y0, storage_x0 = (int(value) for value in level0_shape)

    candidates = []
    for level, storage_shape in level_shapes_zyx.items():
        storage_z, storage_y, storage_x = (int(value) for value in storage_shape)
        logical_shape = (
            max(1, min(storage_z, int(math.ceil(logical_z0 * storage_z / storage_z0)))),
            max(1, min(storage_y, int(math.ceil(logical_y0 * storage_y / storage_y0)))),
            max(1, min(storage_x, int(math.ceil(logical_x0 * storage_x / storage_x0)))),
        )
        max_xy = max(logical_shape[1], logical_shape[2])
        candidates.append((int(level), logical_shape, max_xy))

    large_enough = [candidate for candidate in candidates if candidate[2] >= target_size]
    if large_enough:
        return min(large_enough, key=lambda candidate: (candidate[2], candidate[0]))[:2]
    return max(candidates, key=lambda candidate: (candidate[2], -candidate[0]))[:2]


def read_qc_mip_for_file_channel(ims_path, logical_channel, target_size=400):
    """Read a fast, aspect-preserving QC MIP from the Imaris image pyramid.

    Unlike the main GUI and Cellpose readers, this function deliberately uses
    a reduced Imaris resolution level. It chooses the smallest stored level
    that is still at least ``target_size`` pixels along its longest logical XY
    axis, avoiding both a full level-0 read and unnecessary upsampling.
    """
    with h5py.File(ims_path, "r") as h5:
        mapping = map_channels(h5, verbose=False)
        if logical_channel not in mapping:
            return None

        channel_index = int(mapping[logical_channel])
        timepoint_path = "TimePoint 0"
        dataset_group = h5.get("DataSet")
        if dataset_group is None:
            raise RuntimeError("DataSet is missing.")

        level_paths = {}
        level_shapes = {}
        for level_name in dataset_group.keys():
            match = re.fullmatch(r"ResolutionLevel\s+(\d+)", str(level_name))
            if match is None:
                continue
            level = int(match.group(1))
            data_path = (
                f"DataSet/{level_name}/{timepoint_path}/"
                f"Channel {channel_index}/Data"
            )
            if data_path not in h5:
                continue
            level_paths[level] = data_path
            level_shapes[level] = tuple(int(value) for value in h5[data_path].shape)

        if not level_paths:
            raise RuntimeError(
                f"No pyramid data found for physical Channel {channel_index}."
            )

        logical_shape = get_imaris_logical_shape_zyx(h5)
        level, level_logical_shape = _choose_qc_resolution_level(
            level_shapes,
            logical_shape,
            target_size,
        )
        logical_z, logical_y, logical_x = level_logical_shape
        volume = np.asarray(
            h5[level_paths[level]][:logical_z, :logical_y, :logical_x]
        )
        return np.asarray(np.max(volume, axis=0))


# ============================================================================
# BEGIN GENERATED MODULE: detection.py
# ============================================================================

"""Exposure processing and Cellpose instance detection."""
# =============================================================================
# MANUAL WINDOWING — THIS EXACT ARRAY IS GIVEN TO CELLPOSE
# =============================================================================

def apply_manual_exposure(raw_image, black_point, white_point):
    """
    Convert native raw fluorescence to the exact 0..1 image Cellpose receives.

        raw <= black -> 0
        raw >= white -> 1
        between      -> linear interpolation
    """
    black_point = float(black_point)
    white_point = float(white_point)

    if not np.isfinite(black_point) or not np.isfinite(white_point):
        raise ValueError("Exposure black/white values must be finite.")

    if white_point <= black_point:
        raise ValueError(
            f"White point ({white_point}) must exceed black point "
            f"({black_point})."
        )

    image = np.asarray(raw_image, dtype=np.float32)
    windowed = (image - black_point) / (white_point - black_point)
    return np.clip(windowed, 0.0, 1.0).astype(np.float32)


def suggest_exposure_from_mip(mip):
    finite = np.asarray(mip, dtype=np.float32)
    finite = finite[np.isfinite(finite)]

    if finite.size == 0:
        return 0.0, 1.0, 1.0

    if finite.size > EXPOSURE_HISTOGRAM_SAMPLE_PIXELS:
        step = max(1, finite.size // EXPOSURE_HISTOGRAM_SAMPLE_PIXELS)
        finite = finite[::step][:EXPOSURE_HISTOGRAM_SAMPLE_PIXELS]

    black = float(np.percentile(finite, DEFAULT_BLACK_PERCENTILE))
    white = float(np.percentile(finite, DEFAULT_WHITE_PERCENTILE))
    raw_max = float(np.max(finite))

    if white <= black:
        white = max(black + 1.0, raw_max)

    slider_max = max(raw_max, white, black + 1.0)

    # Common 12-bit acquisitions are easier to manipulate on an Imaris-like
    # 0..4095 axis even if this particular specimen does not hit saturation.
    if slider_max <= 4095.0:
        slider_max = 4095.0

    return black, white, slider_max


def suggest_setup_preview_white(mip):
    """Return a bright, robust display-only white point in the 200..400 range."""
    values = np.asarray(mip, dtype=np.float32)
    values = values[np.isfinite(values)]

    if values.size == 0:
        return float(SETUP_PREVIEW_WHITE_MIN)

    if values.size > EXPOSURE_HISTOGRAM_SAMPLE_PIXELS:
        step = max(1, values.size // EXPOSURE_HISTOGRAM_SAMPLE_PIXELS)
        values = values[::step][:EXPOSURE_HISTOGRAM_SAMPLE_PIXELS]

    robust_white = float(
        np.percentile(values, SETUP_PREVIEW_WHITE_PERCENTILE)
    )
    if not np.isfinite(robust_white):
        robust_white = float(SETUP_PREVIEW_WHITE_MIN)

    return float(np.clip(
        robust_white,
        SETUP_PREVIEW_WHITE_MIN,
        SETUP_PREVIEW_WHITE_MAX,
    ))


# =============================================================================
# CELLPPOSE — NORMALIZATION EXPLICITLY DISABLED
# =============================================================================

def resolve_cellpose_pretrained_model():
    """Return the configured local model path, or native cpsam_v2 when blank."""
    configured = str(CELLPOSE_MODEL_PATH).strip()

    if not configured:
        return NATIVE_CELLPPOSE_MODEL, "builtin"

    model_path = Path(configured).expanduser()

    if not model_path.is_file():
        raise FileNotFoundError(
            "CELLPOSE_MODEL_PATH was set, but the model file does not exist:\n"
            f"  {model_path.resolve()}\n\n"
            "Either correct CELLPOSE_MODEL_PATH or leave it empty to use "
            f"Cellpose's built-in {NATIVE_CELLPPOSE_MODEL!r} model."
        )

    return str(model_path.resolve()), "local_file"


def load_model(device):
    """Load the configured local Cellpose model or native cpsam_v2 fallback."""
    pretrained_model, model_source = resolve_cellpose_pretrained_model()

    cp_model = models.CellposeModel(
        gpu=torch.cuda.is_available(),
        pretrained_model=pretrained_model,
    )

    return {
        "kind": "cellpose",
        "model": cp_model,
        "pretrained_model": pretrained_model,
        "model_source": model_source,
        "native_model": (
            NATIVE_CELLPPOSE_MODEL
            if model_source == "builtin"
            else None
        ),
    }

def _cellpose_eval_normalization_off(cp_model, image_01, cfg):
    """
    Run Cellpose while GUARANTEEING that its own intensity normalization is off.

    We inspect the installed Cellpose eval signature at runtime because Cellpose
    versions differ.  If the installed version exposes no `normalize` argument,
    fail rather than silently allowing hidden auto-exposure.
    """
    import inspect

    eval_signature = inspect.signature(cp_model.eval)

    if "normalize" not in eval_signature.parameters:
        raise RuntimeError(
            "This installed Cellpose version does not expose a `normalize` "
            "argument in CellposeModel.eval(). This workflow refuses to run "
            "because it cannot guarantee that manual exposure will be preserved."
        )

    kwargs = {
        "channels": [0, 0],
        "diameter": float(cfg["model_radius_px"] * 2.0),
        "cellprob_threshold": float(WINDOWED_CELLPOSE_CELLPROB_THRESHOLD),
        "flow_threshold": float(WINDOWED_CELLPOSE_FLOW_THRESHOLD),
        "resample": False,
        "normalize": False,
    }

    # Explicitly disable inversion too when supported.
    if "invert" in eval_signature.parameters:
        kwargs["invert"] = False

    return cp_model.eval(
        np.asarray(image_01, dtype=np.float32),
        **kwargs,
    )


def _resize_label_image_nearest(labels, target_shape):
    labels = np.asarray(labels)
    h, w = target_shape

    if labels.shape[:2] == (h, w):
        return labels

    resized = ndi.zoom(
        labels,
        (
            h / labels.shape[0],
            w / labels.shape[1],
        ),
        order=0,
    )

    return resized[:h, :w]


def run_windowed_cellpose_instances(
    loaded_model,
    windowed_mip,
    cfg,
    return_labels=False,
):
    """Return the mask and accepted centroids, areas, and optionally labels."""
    if loaded_model["kind"] != "cellpose":
        raise RuntimeError(
            "Manual-exposure mode requires a native Cellpose model."
        )

    masks, flows, _ = _cellpose_eval_normalization_off(
        loaded_model["model"],
        windowed_mip,
        cfg,
    )

    masks = np.asarray(masks)

    if masks.ndim != 2:
        masks = np.squeeze(masks)

    if masks.ndim != 2:
        raise RuntimeError(f"Unexpected Cellpose masks shape: {masks.shape}")

    masks = _resize_label_image_nearest(
        masks,
        windowed_mip.shape[:2],
    ).astype(np.int32)

    labels = np.unique(masks)
    labels = labels[labels > 0]

    centers = []
    areas = []
    accepted_labels = []

    for label in labels:
        yy, xx = np.where(masks == label)
        area = int(len(yy))

        if area == 0:
            continue

        if (
            WINDOWED_MIN_INSTANCE_AREA_PX is not None
            and area < int(WINDOWED_MIN_INSTANCE_AREA_PX)
        ):
            continue

        if (
            WINDOWED_MAX_INSTANCE_AREA_PX is not None
            and area > int(WINDOWED_MAX_INSTANCE_AREA_PX)
        ):
            continue

        # Geometric centroid of the Cellpose object.  No raw-fluorescence
        # recentering and no probability-peak recentering are performed.
        centers.append([
            float(np.mean(yy)),
            float(np.mean(xx)),
        ])
        areas.append(area)
        accepted_labels.append(int(label))

    if not centers:
        result = (
            masks,
            np.empty((0, 2), dtype=np.float32),
            np.empty((0,), dtype=np.int32),
        )
        if return_labels:
            return result + (np.empty((0,), dtype=np.int32),)
        return result

    result = (
        masks,
        np.asarray(centers, dtype=np.float32),
        np.asarray(areas, dtype=np.int32),
    )
    if return_labels:
        return result + (np.asarray(accepted_labels, dtype=np.int32),)
    return result


# =============================================================================
# GUI
# =============================================================================

def _load_previous_exposure_settings():
    if not LOAD_PREVIOUS_EXPOSURE_SETTINGS:
        return {}

    if not EXPOSURE_SETTINGS_JSON.exists():
        return {}

    try:
        import json
        payload = json.loads(
            EXPOSURE_SETTINGS_JSON.read_text(encoding="utf-8")
        )
        return payload.get("channels", {})
    except Exception as exc:
        print(
            f"Could not load previous exposure settings from "
            f"{EXPOSURE_SETTINGS_JSON}: {exc}"
        )
        return {}


def _save_exposure_settings(
    selection,
    ims_files,
    destination=None,
):
    import json
    from datetime import datetime

    destination = Path(destination or EXPOSURE_SETTINGS_JSON)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Keep "channels" for backward compatibility with older versions; it
    # contains the series-average exposure values.
    payload = {
        "created": datetime.now().isoformat(
            timespec="seconds"
        ),
        "workflow": (
            "per_image_manual_window_with_series_average_fallback_"
            "plus_bilateral_manual_landmarks_and_rotation"
        ),
        "cellpose_cellprob_threshold": float(
            WINDOWED_CELLPOSE_CELLPROB_THRESHOLD
        ),
        "cellpose_flow_threshold": float(
            WINDOWED_CELLPOSE_FLOW_THRESHOLD
        ),
        "predicted_spot_diameter_um": float(
            PREDICTED_SPOT_DIAMETER_UM
        ),
        "predicted_spot_radius_um": float(
            PREDICTED_SPOT_RADIUS_UM
        ),
        "channels": selection[
            "series_average"
        ],
        "series_average": selection[
            "series_average"
        ],
        "per_file": selection[
            "per_file"
        ],
        "manual_landmarks_yx": selection[
            "manual_landmarks_yx"
        ],
        "rotation": selection.get(
            "rotation",
            {},
        ),
        "enabled_channels": selection.get(
            "enabled_channels",
            list(CHANNEL_PROCESSING_ORDER),
        ),
        "counting_regions": selection.get(
            "counting_regions",
            {
                channel: DEFAULT_COUNTING_REGION
                for channel in CHANNEL_PROCESSING_ORDER
            },
        ),
        "custom_counting_rois_yx": selection.get(
            "custom_counting_rois_yx",
            {},
        ),
        "custom_counting_roi_modes": selection.get(
            "custom_counting_roi_modes",
            {},
        ),
        "files": [
            Path(path).name
            for path in ims_files
        ],
    }

    destination.write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Exposure/landmark settings saved: "
        f"{destination.resolve()}"
    )
    return destination


# ============================================================================
# BEGIN GENERATED MODULE: geometry.py
# ============================================================================

"""Landmark, Z-coordinate, hemisphere, rectangle, and ROI geometry."""
# =============================================================================
# Z / PHYSICAL COORDINATES
# =============================================================================

def choose_z_indices(volume_zyx, centroids_yx, cfg, geo):
    """
    Preserve the script's configured Z-placement policy.

    stack_center is the normal mode and does not inspect fluorescence.
    optical mode retains a local raw-stack Z estimate as an optional legacy
    mode, but XY coordinates are never moved by fluorescence.
    """
    if len(centroids_yx) == 0:
        return np.empty((0,), dtype=np.float32)

    mode = str(Z_PLACEMENT_MODE).strip().lower()

    if mode == "stack_center":
        return np.full(
            len(centroids_yx),
            (geo["nz"] - 1) / 2.0,
            dtype=np.float32,
        )

    if mode != "optical":
        raise ValueError(
            f"Unsupported Z_PLACEMENT_MODE={Z_PLACEMENT_MODE!r}"
        )

    radius = int(cfg.get("z_localization_radius_px", 8))
    z_values = []
    nz, ny, nx = volume_zyx.shape

    for cy, cx in centroids_yx:
        iy = int(round(float(cy)))
        ix = int(round(float(cx)))

        y0 = max(0, iy - radius)
        y1 = min(ny, iy + radius + 1)
        x0 = max(0, ix - radius)
        x1 = min(nx, ix + radius + 1)

        local = np.asarray(
            volume_zyx[:, y0:y1, x0:x1],
            dtype=np.float32,
        )

        profile = np.max(local, axis=(1, 2))
        z_values.append(float(np.argmax(profile)))

    return np.asarray(z_values, dtype=np.float32)


def detector_coordinates_to_imaris_xyz(centroids_yx, z_indices, geo):
    if len(centroids_yx) == 0:
        return np.empty((0, 3), dtype=np.float32)

    centroids_yx = np.asarray(centroids_yx, dtype=np.float64)
    z_indices = np.asarray(z_indices, dtype=np.float64)

    y = centroids_yx[:, 0]
    x = centroids_yx[:, 1]

    # Cellpose centroid X/Y coordinates are expressed in the cropped LOGICAL
    # image. geo["nx"]/geo["ny"] are deliberately those exact logical sizes.
    x_um = geo["min_x"] + ((x + 0.5) / float(geo["nx"])) * (
        geo["max_x"] - geo["min_x"]
    )

    y_um = geo["min_y"] + ((y + 0.5) / float(geo["ny"])) * (
        geo["max_y"] - geo["min_y"]
    )

    z_um = geo["min_z"] + ((z_indices + 0.5) / geo["nz"]) * (
        geo["max_z"] - geo["min_z"]
    )

    if str(Z_PLACEMENT_MODE).strip().lower() == "stack_center":
        z_center_um = (
            (geo["min_z"] + geo["max_z"]) / 2.0
            + float(Z_CENTER_OFFSET_UM)
        )
        z_center_um = float(
            np.clip(
                z_center_um,
                geo["min_z"],
                geo["max_z"],
            )
        )
        z_um[:] = z_center_um

    return np.column_stack(
        [x_um, y_um, z_um]
    ).astype(np.float32)


def manual_landmarks_yx_to_imaris_xyz(
    h5,
    landmarks_yx,
):
    """Convert all seven GUI click locations to physical Imaris XYZ."""
    geo = get_image_geometry(
        h5,
        verbose=False,
    )

    z_center_um = (
        (geo["min_z"] + geo["max_z"]) / 2.0
        + float(Z_CENTER_OFFSET_UM)
    )

    z_center_um = float(
        np.clip(
            z_center_um,
            geo["min_z"],
            geo["max_z"],
        )
    )

    result = {}

    for key in MANUAL_GUI_LANDMARKS:
        if key not in landmarks_yx:
            continue

        y = float(landmarks_yx[key][0])
        x = float(landmarks_yx[key][1])

        x_um = (
            geo["min_x"]
            + ((x + 0.5) / float(geo["nx"]))
            * (geo["max_x"] - geo["min_x"])
        )

        y_um = (
            geo["min_y"]
            + ((y + 0.5) / float(geo["ny"]))
            * (geo["max_y"] - geo["min_y"])
        )

        result[key] = np.asarray(
            [[x_um, y_um, z_center_um]],
            dtype=np.float32,
        )

    return result


def hemisphere_manual_predictions(
    all_landmarks_xyz,
    hemisphere,
):
    """Map bilateral GUI landmarks onto canonical ce/si/bo/to output names."""
    hemisphere = str(hemisphere).upper()

    if hemisphere not in ("L", "R"):
        raise ValueError(
            f"Unknown hemisphere {hemisphere!r}"
        )

    return {
        "ce": all_landmarks_xyz["ce"],
        "si": all_landmarks_xyz[f"si_{hemisphere}"],
        "bo": all_landmarks_xyz[f"bo_{hemisphere}"],
        "to": all_landmarks_xyz[f"to_{hemisphere}"],
    }




def build_counting_rectangle_yx(manual_landmarks_yx, hemisphere, margin_px=COUNTING_ROI_MARGIN_PX):
    """Return a midline-aligned L/R counting rectangle as four (y,x) corners.

    Geometry follows the landmark construction requested for the GUI:
      * medial edge: the directed bottom->top midline;
      * top/bottom edges: perpendicular to that midline through to_H / bo_H;
      * lateral edge: parallel to the midline through si_H;
      * ``margin_px`` expands only the top, bottom and OUTER lateral edges.
        The midline remains an exact hard medial border with zero padding.
    """
    hemi = str(hemisphere).upper()
    needed = ("rot_bottom", "rot_top", f"bo_{hemi}", f"to_{hemi}", f"si_{hemi}")
    if not all(k in manual_landmarks_yx for k in needed):
        return None

    y0, x0 = map(float, manual_landmarks_yx["rot_bottom"])
    y1, x1 = map(float, manual_landmarks_yx["rot_top"])
    # Work in conventional (x,y) vectors, while returning (y,x).
    axis = np.asarray([x1 - x0, y1 - y0], dtype=np.float64)
    norm = float(np.linalg.norm(axis))
    if norm <= 1e-12:
        return None
    u = axis / norm
    n = np.asarray([-u[1], u[0]], dtype=np.float64)
    origin = np.asarray([x0, y0], dtype=np.float64)

    def proj(key):
        y, x = map(float, manual_landmarks_yx[key])
        v = np.asarray([x, y], dtype=np.float64) - origin
        return float(np.dot(v, u)), float(np.dot(v, n))

    t_bo, _ = proj(f"bo_{hemi}")
    t_to, _ = proj(f"to_{hemi}")
    _, s_si = proj(f"si_{hemi}")

    margin = float(max(0.0, margin_px))
    t_min = min(t_bo, t_to) - margin
    t_max = max(t_bo, t_to) + margin

    # The medial edge is a HARD border at the midline (normal coordinate 0).
    # Apply safety padding only outwards, beyond the hemisphere's lateral
    # si-defined edge. Never expand across the midline into the other side.
    if s_si >= 0.0:
        s_min = 0.0
        s_max = s_si + margin
    else:
        s_min = s_si - margin
        s_max = 0.0

    corners_xy = [
        origin + t_min * u + s_min * n,
        origin + t_min * u + s_max * n,
        origin + t_max * u + s_max * n,
        origin + t_max * u + s_min * n,
    ]
    return np.asarray([[p[1], p[0]] for p in corners_xy], dtype=np.float64)


def build_counting_region_divider_yx(
    manual_landmarks_yx,
    hemisphere,
    margin_px=COUNTING_ROI_MARGIN_PX,
):
    """Return the centre-based dorsal/ventral divider as two (y, x) points."""
    hemi = str(hemisphere).upper()
    needed = (
        "ce", "rot_bottom", "rot_top",
        f"bo_{hemi}", f"to_{hemi}", f"si_{hemi}",
    )
    if not all(k in manual_landmarks_yx for k in needed):
        return None

    y0, x0 = map(float, manual_landmarks_yx["rot_bottom"])
    y1, x1 = map(float, manual_landmarks_yx["rot_top"])
    axis = np.asarray([x1 - x0, y1 - y0], dtype=np.float64)
    norm = float(np.linalg.norm(axis))
    if norm <= 1e-12:
        return None

    u = axis / norm
    n = np.asarray([-u[1], u[0]], dtype=np.float64)
    origin = np.asarray([x0, y0], dtype=np.float64)

    def proj(key):
        y, x = map(float, manual_landmarks_yx[key])
        v = np.asarray([x, y], dtype=np.float64) - origin
        return float(np.dot(v, u)), float(np.dot(v, n))

    t_bo, _ = proj(f"bo_{hemi}")
    t_to, _ = proj(f"to_{hemi}")
    t_ce, _ = proj("ce")
    _, s_si = proj(f"si_{hemi}")

    margin = float(max(0.0, margin_px))
    t_min = min(t_bo, t_to) - margin
    t_max = max(t_bo, t_to) + margin
    # Clamp an accidentally outlying ce click to the rectangle so a selected
    # half can never invert or extend beyond the normal counting region.
    t_divider = float(np.clip(t_ce, t_min, t_max))

    if s_si >= 0.0:
        s_min, s_max = 0.0, s_si + margin
    else:
        s_min, s_max = s_si - margin, 0.0

    endpoints_xy = [
        origin + t_divider * u + s_min * n,
        origin + t_divider * u + s_max * n,
    ]
    return np.asarray(
        [[p[1], p[0]] for p in endpoints_xy],
        dtype=np.float64,
    )


def build_selected_counting_region_polygon_yx(
    manual_landmarks_yx,
    hemisphere,
    counting_region,
    margin_px=COUNTING_ROI_MARGIN_PX,
):
    """Return the selected rectangle/half as a four-corner (y, x) polygon."""
    region = str(counting_region).strip().lower()
    if region not in COUNTING_REGION_MODES:
        return None

    corners = build_counting_rectangle_yx(
        manual_landmarks_yx,
        hemisphere,
        margin_px=margin_px,
    )
    if corners is None or region == "whole":
        return corners

    divider = build_counting_region_divider_yx(
        manual_landmarks_yx,
        hemisphere,
        margin_px=margin_px,
    )
    if divider is None:
        return None

    # Rectangle corner order is: bottom/medial, bottom/lateral,
    # top/lateral, top/medial. Divider order is medial, lateral.
    if region == "ventral":
        return np.asarray(
            [corners[0], corners[1], divider[1], divider[0]],
            dtype=np.float64,
        )
    return np.asarray(
        [divider[0], divider[1], corners[2], corners[3]],
        dtype=np.float64,
    )


def points_in_polygon_yx(points_yx, polygon_yx):
    """Vectorized even-odd test; polygon-edge points count as inside."""
    points = np.asarray(points_yx, dtype=np.float64)
    polygon = np.asarray(polygon_yx, dtype=np.float64)
    if len(points) == 0:
        return np.empty((0,), dtype=bool)
    if polygon.ndim != 2 or polygon.shape[1] != 2 or len(polygon) < 3:
        return np.ones(len(points), dtype=bool)

    py = points[:, 0]
    px = points[:, 1]
    inside = np.zeros(len(points), dtype=bool)
    on_edge = np.zeros(len(points), dtype=bool)
    tolerance = 1e-7

    for i in range(len(polygon)):
        y1, x1 = polygon[i]
        y2, x2 = polygon[(i + 1) % len(polygon)]
        dx = x2 - x1
        dy = y2 - y1

        cross = (px - x1) * dy - (py - y1) * dx
        within = (
            (px >= min(x1, x2) - tolerance)
            & (px <= max(x1, x2) + tolerance)
            & (py >= min(y1, y2) - tolerance)
            & (py <= max(y1, y2) + tolerance)
        )
        on_edge |= (np.abs(cross) <= tolerance) & within

        crosses = (y1 > py) != (y2 > py)
        x_intersection = dx * (py - y1) / (
            dy if abs(dy) > tolerance else tolerance
        ) + x1
        inside ^= crosses & (px < x_intersection)

    return inside | on_edge


def custom_roi_keep_mask_yx(
    points_yx,
    polygon_yx,
    mode=DEFAULT_CUSTOM_ROI_MODE,
):
    """Return points inside an inclusion ROI or outside an exclusion ROI."""
    roi_mode = str(mode).strip().lower()
    if roi_mode not in CUSTOM_ROI_MODES:
        roi_mode = DEFAULT_CUSTOM_ROI_MODE
    inside = points_in_polygon_yx(points_yx, polygon_yx)
    return ~inside if roi_mode == "exclude" else inside


def counting_rectangle_mask_yx(
    points_yx,
    manual_landmarks_yx,
    hemisphere,
    margin_px=COUNTING_ROI_MARGIN_PX,
    counting_region=DEFAULT_COUNTING_REGION,
):
    """Mask points to the whole, dorsal, or ventral rectangle region."""
    hemi = str(hemisphere).upper()
    needed = ("ce", "rot_bottom", "rot_top", f"bo_{hemi}", f"to_{hemi}", f"si_{hemi}")
    if not all(k in manual_landmarks_yx for k in needed):
        return np.ones(len(points_yx), dtype=bool)

    y0, x0 = map(float, manual_landmarks_yx["rot_bottom"])
    y1, x1 = map(float, manual_landmarks_yx["rot_top"])
    axis = np.asarray([x1 - x0, y1 - y0], dtype=np.float64)
    norm = float(np.linalg.norm(axis))
    if norm <= 1e-12:
        return np.ones(len(points_yx), dtype=bool)
    u = axis / norm
    n = np.asarray([-u[1], u[0]], dtype=np.float64)
    origin = np.asarray([x0, y0], dtype=np.float64)

    def landmark_proj(key):
        y, x = map(float, manual_landmarks_yx[key])
        v = np.asarray([x, y], dtype=np.float64) - origin
        return float(np.dot(v, u)), float(np.dot(v, n))

    t_bo, _ = landmark_proj(f"bo_{hemi}")
    t_to, _ = landmark_proj(f"to_{hemi}")
    t_ce, _ = landmark_proj("ce")
    _, s_si = landmark_proj(f"si_{hemi}")
    margin = float(max(0.0, margin_px))
    t_min, t_max = min(t_bo, t_to) - margin, max(t_bo, t_to) + margin

    # Same hard-midline rule as the GUI rectangle: no medial padding.
    if s_si >= 0.0:
        s_min, s_max = 0.0, s_si + margin
    else:
        s_min, s_max = s_si - margin, 0.0

    pts = np.asarray(points_yx, dtype=np.float64)
    xy = np.stack([pts[:, 1], pts[:, 0]], axis=1)
    rel = xy - origin[None, :]
    t = rel @ u
    s = rel @ n
    keep = (t >= t_min) & (t <= t_max) & (s >= s_min) & (s <= s_max)

    region = str(counting_region).strip().lower()
    if region not in COUNTING_REGION_MODES:
        raise ValueError(
            f"Unknown counting region {counting_region!r}; expected one of "
            f"{COUNTING_REGION_MODES}."
        )

    # The midline direction is anatomical bottom -> top. Therefore increasing
    # longitudinal coordinate is dorsal, independent of how the image appears
    # on screen. Points exactly on the centre divider are retained.
    t_divider = float(np.clip(t_ce, t_min, t_max))
    if region == "dorsal":
        keep &= t >= t_divider
    elif region == "ventral":
        keep &= t <= t_divider

    return keep


def filter_split_predictions_to_counting_rectangles(
    split_predictions,
    manual_landmarks_yx,
    h5,
    counting_regions=None,
    custom_rois_yx=None,
    custom_roi_modes=None,
):
    """Apply anatomical selection and inclusive/exclusive custom polygons."""
    if counting_regions is None:
        region_by_channel = {
            channel: DEFAULT_COUNTING_REGION
            for channel in CHANNEL_PROCESSING_ORDER
        }
    elif isinstance(counting_regions, str):
        # Backward compatibility with the early single-region settings form.
        region_by_channel = {
            channel: counting_regions
            for channel in CHANNEL_PROCESSING_ORDER
        }
    else:
        region_by_channel = {
            channel: str(
                counting_regions.get(channel, DEFAULT_COUNTING_REGION)
            ).strip().lower()
            for channel in CHANNEL_PROCESSING_ORDER
        }

    custom_rois_yx = custom_rois_yx or {}
    custom_roi_modes = custom_roi_modes or {}

    geo = get_image_geometry(h5, verbose=False)
    x_span = float(geo["max_x"] - geo["min_x"])
    y_span = float(geo["max_y"] - geo["min_y"])
    nx = float(geo["nx"])
    ny = float(geo["ny"])

    def xyz_to_yx(xyz):
        xyz = normalize_xyz(xyz)
        if len(xyz) == 0:
            return np.empty((0, 2), dtype=np.float64)
        px = ((xyz[:, 0].astype(np.float64) - geo["min_x"]) / x_span) * nx - 0.5
        py = ((xyz[:, 1].astype(np.float64) - geo["min_y"]) / y_span) * ny - 0.5
        return np.stack([py, px], axis=1)

    filtered = {"L": {}, "R": {}}
    counts = {"L": {}, "R": {}}
    for hemi in ("L", "R"):
        for group_name, xyz in split_predictions[hemi].items():
            xyz = normalize_xyz(xyz)
            if len(xyz) == 0:
                filtered[hemi][group_name] = xyz
                counts[hemi][group_name] = (0, 0)
                continue
            yx = xyz_to_yx(xyz)
            keep = counting_rectangle_mask_yx(
                yx,
                manual_landmarks_yx,
                hemi,
                counting_region=region_by_channel.get(
                    group_name,
                    DEFAULT_COUNTING_REGION,
                ),
            )
            channel_custom_roi = custom_rois_yx.get(group_name)
            custom_polygon = (
                channel_custom_roi.get(hemi)
                if isinstance(channel_custom_roi, dict)
                else channel_custom_roi
            )
            if (
                custom_polygon is not None
                and len(custom_polygon) >= CUSTOM_ROI_MIN_VERTICES
            ):
                channel_roi_modes = custom_roi_modes.get(group_name, {})
                if isinstance(channel_roi_modes, dict):
                    roi_mode = str(channel_roi_modes.get(
                        hemi,
                        DEFAULT_CUSTOM_ROI_MODE,
                    )).strip().lower()
                else:
                    roi_mode = str(channel_roi_modes).strip().lower()
                if roi_mode not in CUSTOM_ROI_MODES:
                    roi_mode = DEFAULT_CUSTOM_ROI_MODE
                keep &= custom_roi_keep_mask_yx(
                    yx,
                    custom_polygon,
                    roi_mode,
                )
            filtered[hemi][group_name] = xyz[keep].astype(np.float32, copy=False)
            counts[hemi][group_name] = (int(len(xyz)), int(np.count_nonzero(keep)))
    return filtered, counts


def split_predictions_by_midline(predictions, manual_landmarks_yx, h5):
    """Split predicted XYZ spot clouds into left/right hemispheres using the directed midline.

    The side assignment is independent of rotation. The directed line from
    rot_bottom -> rot_top defines anatomical LEFT vs RIGHT.

    In image coordinates (X right, Y down), using the directed midline vector:
      - signed cross product < 0  -> LEFT side
      - signed cross product > 0  -> RIGHT side

    Because the user explicitly marks anatomical bottom and top, this remains
    correct even if the image is upside down on screen.
    """
    if not all(k in manual_landmarks_yx for k in ROTATION_LANDMARK_KEYS):
        raise RuntimeError(
            'Midline points rot_bottom and rot_top are required to split predicted spots into left and right outputs.'
        )

    geo = get_image_geometry(h5, verbose=False)
    y_bottom, x_bottom = map(float, manual_landmarks_yx['rot_bottom'])
    y_top, x_top = map(float, manual_landmarks_yx['rot_top'])

    dx = x_top - x_bottom
    dy = y_top - y_bottom
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        raise RuntimeError(
            'Midline bottom/top points are identical; cannot split predictions by side.'
        )

    x_span = float(geo['max_x'] - geo['min_x'])
    y_span = float(geo['max_y'] - geo['min_y'])
    nx = float(geo['nx'])
    ny = float(geo['ny'])

    def xyz_to_yx(xyz):
        if xyz is None or len(xyz) == 0:
            return np.empty((0, 2), dtype=np.float64)
        px = ((xyz[:, 0].astype(np.float64) - geo['min_x']) / x_span) * nx - 0.5
        py = ((xyz[:, 1].astype(np.float64) - geo['min_y']) / y_span) * ny - 0.5
        return np.stack([py, px], axis=1)

    split = {'L': {}, 'R': {}}
    side_counts = {}

    for group_name, xyz in predictions.items():
        if xyz is None or len(xyz) == 0:
            split['L'][group_name] = np.empty((0, 3), dtype=np.float32)
            split['R'][group_name] = np.empty((0, 3), dtype=np.float32)
            side_counts[group_name] = (0, 0, 0)
            continue

        yx = xyz_to_yx(xyz)
        py = yx[:, 0]
        px = yx[:, 1]

        # Signed 2D cross product in image coordinates.
        cross = dx * (py - y_bottom) - dy * (px - x_bottom)
        eps = 1e-6
        left_mask = cross < -eps
        right_mask = cross > eps
        on_line_mask = ~(left_mask | right_mask)

        # Keep exact-on-midline detections in both outputs so none are lost.
        split['L'][group_name] = xyz[left_mask | on_line_mask].astype(np.float32, copy=False)
        split['R'][group_name] = xyz[right_mask | on_line_mask].astype(np.float32, copy=False)
        side_counts[group_name] = (
            int(np.count_nonzero(left_mask)),
            int(np.count_nonzero(right_mask)),
            int(np.count_nonzero(on_line_mask)),
        )

    return split, side_counts

def compute_rotation_info(manual_landmarks_yx):
    ccw_deg = compute_counterclockwise_rotation_to_vertical_deg(
        manual_landmarks_yx
    )
    return {
        "ccw_deg": ccw_deg,
        "group_name": format_rotation_group_name(ccw_deg),
    }


# ============================================================================
# BEGIN GENERATED MODULE: logging_setup.py
# ============================================================================

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


# ============================================================================
# BEGIN GENERATED MODULE: startup_gui.py
# ============================================================================

"""Themed preflight window for selecting a Neurodot processing job."""

from pathlib import Path
import math



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
        content.grid_columnconfigure(0, weight=1)

        header = tk.Frame(content, bg=GUI_BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        title_block = tk.Frame(header, bg=GUI_BG)
        title_block.pack(side="left", anchor="nw", fill="x", expand=True)
        tk.Label(
            title_block,
            text="START A COUNTING JOB",
            bg=GUI_BG,
            fg=GUI_ACCENT,
            font=("Segoe UI Semibold", 13),
        ).pack(anchor="w", pady=(0, 3))
        tk.Label(
            title_block,
            text="Choose the files and model for this run, then select how to begin.",
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        form = tk.Frame(content, bg=GUI_BG)
        form.grid(row=1, column=0, sticky="nsew")

        self._path_row(form, 2, "INPUT FOLDER", self.input_var, self._browse_input)
        self._path_row(
            form,
            4,
            "OUTPUT FOLDER",
            self.output_var,
            self._browse_output,
            secondary=("Same as input", self._use_input_as_output),
        )

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

        separator = tk.Frame(outer, bg=GUI_BORDER, height=1)
        separator.pack(fill="x", pady=(16, 12))

        actions = tk.Frame(outer, bg=GUI_BG)
        actions.pack(fill="x")
        self._button(actions, "Cancel", self._cancel, width=11).pack(side="right")
        self._button(
            actions,
            "Continue without QC",
            lambda: self._continue(use_quality_review=False),
            width=20,
        ).pack(side="right", padx=(0, 8))
        self._button(
            actions,
            "Continue with image QC",
            lambda: self._continue(use_quality_review=True),
            width=23,
            accent=True,
        ).pack(side="right", padx=(0, 8))

    def _path_row(self, parent, row, label, variable, command, secondary=None):
        tk = self.tk
        tk.Label(
            parent,
            text=label,
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI Semibold", 8),
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 5))

        row_frame = tk.Frame(parent, bg=GUI_BG)
        row_frame.grid(row=row + 1, column=0, columnspan=3, sticky="ew")
        row_frame.grid_columnconfigure(0, weight=1)
        entry = self._entry(row_frame, variable)
        entry.grid(row=0, column=0, sticky="ew")
        self._button(row_frame, "Browse", command, width=9).grid(
            row=0, column=1, padx=(7, 0)
        )
        if secondary is not None:
            secondary_text, secondary_command = secondary
            self._button(
                row_frame,
                secondary_text,
                secondary_command,
                width=13,
            ).grid(row=0, column=2, padx=(7, 0))
        else:
            placeholder = self._button(
                row_frame,
                "",
                lambda: None,
                width=13,
            )
            placeholder.configure(
                state="disabled",
                bg=GUI_BG,
                disabledforeground=GUI_BG,
                highlightbackground=GUI_BG,
                cursor="arrow",
            )
            placeholder.grid(row=0, column=2, padx=(7, 0))

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

    def _use_input_as_output(self):
        self.output_var.set(self.input_var.get().strip())

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


# ============================================================================
# BEGIN GENERATED MODULE: progress_gui.py
# ============================================================================

"""Small themed progress window for console-free Neurodot builds."""

from pathlib import Path
import os
import queue
import threading



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


# ============================================================================
# BEGIN GENERATED MODULE: qc_io.py
# ============================================================================

"""Lightweight Imaris pyramid reading used before Cellpose is imported."""

import math
import re




def _decode_h5_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, np.bytes_)):
        return bytes(value).decode("utf-8", errors="ignore").rstrip("\x00")
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return ""
        if value.dtype.kind == "S":
            return b"".join(bytes(item) for item in value.ravel()).decode(
                "utf-8", errors="ignore"
            ).rstrip("\x00")
        if value.dtype.kind == "U":
            return "".join(str(item) for item in value.ravel()).rstrip("\x00")
        if value.dtype.kind in ("u", "i"):
            try:
                return bytes(
                    int(item)
                    for item in value.ravel()
                    if 0 <= int(item) <= 255
                ).decode("utf-8", errors="ignore").rstrip("\x00")
            except Exception:
                pass
        if value.size == 1:
            return _decode_h5_text(value.flat[0])
        return str(value)
    if isinstance(value, np.generic):
        return str(value.item())
    return str(value)


def _parse_float(value):
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    match = re.search(
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?",
        _decode_h5_text(value),
    )
    return float(match.group(0)) if match else None


def _logical_channel_from_wavelength(wavelength_nm):
    wavelength = float(wavelength_nm)
    if not math.isfinite(wavelength):
        return None
    for channel in ("405", "g", "r", "b"):
        low, high = CHANNEL_WAVELENGTH_BANDS_NM[channel]
        if low is not None and wavelength < float(low):
            continue
        if high is not None and wavelength >= float(high):
            continue
        return channel
    return None


def _map_channels(h5):
    mapping = {}
    dataset_info = h5.get("DataSetInfo")
    if dataset_info is None:
        raise RuntimeError("DataSetInfo is missing.")

    for key in dataset_info.keys():
        if not str(key).startswith("Channel"):
            continue
        digits = "".join(character for character in str(key) if character.isdigit())
        if not digits:
            continue
        channel_index = int(digits)
        group = dataset_info[key]
        raw_name = _decode_h5_text(group.attrs.get("Name", "")).strip().lower()

        raw_wavelength = ""
        for attribute_name, raw_value in group.attrs.items():
            if "emission" in str(attribute_name).lower():
                raw_wavelength = _decode_h5_text(raw_value)
                break
        if not raw_wavelength:
            for attribute_name, raw_value in group.attrs.items():
                if "wavelength" in str(attribute_name).lower():
                    raw_wavelength = _decode_h5_text(raw_value)
                    break

        wavelength = _parse_float(raw_wavelength) if raw_wavelength else None
        matched = None
        if wavelength is not None and math.isfinite(float(wavelength)):
            matched = _logical_channel_from_wavelength(wavelength)
        elif wavelength is None:
            for target, settings in TARGET_CONFIG.items():
                if raw_name in settings["aliases"]:
                    matched = target
                    break

        if matched is not None and matched not in mapping:
            mapping[matched] = channel_index
    return mapping


def _level0_shape_zyx(h5):
    path = "DataSet/ResolutionLevel 0/TimePoint 0"
    if path not in h5:
        raise RuntimeError(f"Missing {path}")
    timepoint = h5[path]
    channels = sorted(key for key in timepoint if str(key).startswith("Channel"))
    if not channels:
        raise RuntimeError("No channels at ResolutionLevel 0 / TimePoint 0")
    return tuple(int(value) for value in timepoint[channels[0]]["Data"].shape)


def _logical_dimension(image_group, key):
    candidates = (key, key.upper(), key.lower(), f"Size{key.upper()}", f"size{key.upper()}")
    for name in candidates:
        if name in image_group.attrs:
            value = _parse_float(image_group.attrs[name])
            if value is not None and int(round(value)) > 0:
                return int(round(value))
        if name in image_group and isinstance(image_group[name], h5py.Dataset):
            value = _parse_float(image_group[name][()])
            if value is not None and int(round(value)) > 0:
                return int(round(value))
    return None


def _logical_shape_zyx(h5):
    storage_z, storage_y, storage_x = _level0_shape_zyx(h5)
    if "DataSetInfo/Image" not in h5:
        return storage_z, storage_y, storage_x
    image = h5["DataSetInfo/Image"]
    logical_x = _logical_dimension(image, "X") or storage_x
    logical_y = _logical_dimension(image, "Y") or storage_y
    logical_z = _logical_dimension(image, "Z") or storage_z
    if logical_x > storage_x or logical_y > storage_y or logical_z > storage_z:
        raise RuntimeError(
            "Imaris logical dimensions exceed level-0 HDF5 storage shape."
        )
    return logical_z, logical_y, logical_x


def choose_qc_resolution_level(level_shapes_zyx, logical_shape_zyx, target_size):
    """Choose the smallest stored pyramid level that is not below target size."""
    if not level_shapes_zyx:
        raise RuntimeError("No Imaris resolution levels are available.")
    target_size = max(1, int(target_size))
    level0_shape = level_shapes_zyx[min(level_shapes_zyx)]
    logical_z0, logical_y0, logical_x0 = map(int, logical_shape_zyx)
    storage_z0, storage_y0, storage_x0 = map(int, level0_shape)
    candidates = []
    for level, storage_shape in level_shapes_zyx.items():
        storage_z, storage_y, storage_x = map(int, storage_shape)
        logical_shape = (
            max(1, min(storage_z, math.ceil(logical_z0 * storage_z / storage_z0))),
            max(1, min(storage_y, math.ceil(logical_y0 * storage_y / storage_y0))),
            max(1, min(storage_x, math.ceil(logical_x0 * storage_x / storage_x0))),
        )
        candidates.append((int(level), logical_shape, max(logical_shape[1:])))
    large_enough = [item for item in candidates if item[2] >= target_size]
    if large_enough:
        return min(large_enough, key=lambda item: (item[2], item[0]))[:2]
    return max(candidates, key=lambda item: (item[2], -item[0]))[:2]


def read_qc_mip_for_file_channel(ims_path, logical_channel, target_size=400):
    """Read an aspect-preserving MIP from a small stored Imaris pyramid level."""
    with h5py.File(ims_path, "r") as h5:
        mapping = _map_channels(h5)
        if logical_channel not in mapping:
            return None
        channel_index = int(mapping[logical_channel])
        dataset_group = h5.get("DataSet")
        if dataset_group is None:
            raise RuntimeError("DataSet is missing.")

        level_paths = {}
        level_shapes = {}
        for level_name in dataset_group.keys():
            match = re.fullmatch(r"ResolutionLevel\s+(\d+)", str(level_name))
            if match is None:
                continue
            level = int(match.group(1))
            path = (
                f"DataSet/{level_name}/TimePoint 0/"
                f"Channel {channel_index}/Data"
            )
            if path in h5:
                level_paths[level] = path
                level_shapes[level] = tuple(int(value) for value in h5[path].shape)
        if not level_paths:
            raise RuntimeError(
                f"No pyramid data found for physical Channel {channel_index}."
            )

        level, logical_shape = choose_qc_resolution_level(
            level_shapes,
            _logical_shape_zyx(h5),
            target_size,
        )
        logical_z, logical_y, logical_x = logical_shape
        volume = np.asarray(
            h5[level_paths[level]][:logical_z, :logical_y, :logical_x]
        )
        return np.asarray(np.max(volume, axis=0))


# ============================================================================
# BEGIN GENERATED MODULE: quality_review.py
# ============================================================================

"""Pre-analysis, high-resolution overview for series quality control."""

from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import math
import queue
import shutil




EXCLUDED_FOLDER_NAME = "excluded_from_analysis"
OVERVIEW_CHANNELS = ("g", "b", "r", "405")
OVERVIEW_ZOOM_MIN = 0.55
OVERVIEW_ZOOM_MAX = 6.0
OVERVIEW_ZOOM_STEP = 1.20
OVERVIEW_PREVIEW_MAX_SIZE = 400
OVERVIEW_FOREGROUND_WORKERS = 4
OVERVIEW_BACKGROUND_WORKERS = 2
OVERVIEW_EXPOSURE_BLACK_DEFAULT = 0.0
OVERVIEW_EXPOSURE_WHITE_DEFAULT = 400.0
OVERVIEW_EXPOSURE_SLIDER_MAX = 2000.0
OVERVIEW_INCLUDED_BORDER = "#2f7540"
OVERVIEW_INCLUDED_TEXT = "#69a976"
OVERVIEW_EXCLUDED_COLOR = "#ff5555"


def _apply_preview_exposure(raw_image, black_point, white_point):
    """Window a cached QC MIP without importing the Cellpose stack."""
    image = np.asarray(raw_image, dtype=np.float32)
    return np.clip(
        (image - float(black_point)) / (float(white_point) - float(black_point)),
        0.0,
        1.0,
    )


class ImageQualityOverviewWindow:
    """Show every IMS MIP and let the operator exclude poor-quality files."""

    def __init__(
        self,
        ims_files,
        input_dir=None,
        apply_exclusions=True,
        on_initial_previews_ready=None,
    ):
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
        self.on_initial_previews_ready = on_initial_previews_ready
        self.initial_previews_ready_notified = False
        self.selected = {path: True for path in self.ims_files}
        self.current_channel = "g"
        self.zoom = 1.0
        self.result = None
        self.channel_exposure = {
            channel: {
                "black": OVERVIEW_EXPOSURE_BLACK_DEFAULT,
                "white": OVERVIEW_EXPOSURE_WHITE_DEFAULT,
            }
            for channel in OVERVIEW_CHANNELS
        }
        self._updating_exposure_controls = False

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

        exposure_bar = self.tk.Frame(
            self.root,
            bg=GUI_BG,
            padx=14,
            pady=7,
        )
        exposure_bar.pack(fill="x")
        self.tk.Label(
            exposure_bar,
            text="EXPOSURE",
            bg=GUI_BG,
            fg=GUI_MUTED_FG,
            font=("Segoe UI Semibold", 8),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.black_exposure_var = self.tk.DoubleVar(
            value=OVERVIEW_EXPOSURE_BLACK_DEFAULT
        )
        self.white_exposure_var = self.tk.DoubleVar(
            value=OVERVIEW_EXPOSURE_WHITE_DEFAULT
        )
        self._add_exposure_slider(
            exposure_bar,
            "Black",
            self.black_exposure_var,
            self._on_black_exposure_changed,
            row=1,
        )
        self._add_exposure_slider(
            exposure_bar,
            "White",
            self.white_exposure_var,
            self._on_white_exposure_changed,
            row=2,
        )
        reset_exposure_border, _reset_exposure_button = self._bordered_button(
            exposure_bar,
            "Reset",
            self.reset_channel_exposure,
            8,
        )
        reset_exposure_border.grid(
            row=0,
            column=2,
            sticky="e",
            padx=(10, 0),
            pady=(0, 2),
        )
        exposure_bar.grid_columnconfigure(1, weight=1)
        self._load_channel_exposure_controls()

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

    def _add_exposure_slider(
        self,
        parent,
        label,
        variable,
        command,
        row,
    ):
        self.tk.Label(
            parent,
            text=label,
            bg=GUI_BG,
            fg=GUI_FG,
            font=("Segoe UI", 9),
            width=8,
            anchor="w",
        ).grid(row=row, column=0, sticky="w")
        scale = self.tk.Scale(
            parent,
            variable=variable,
            command=command,
            from_=0.0,
            to=OVERVIEW_EXPOSURE_SLIDER_MAX,
            resolution=1.0,
            orient="horizontal",
            showvalue=True,
            length=1400,
            sliderlength=16,
            bg=GUI_BG,
            fg=GUI_FG,
            troughcolor=GUI_CONTROL_BG,
            activebackground=GUI_ACCENT,
            highlightthickness=0,
            borderwidth=0,
            font=("Segoe UI", 8),
        )
        scale.grid(row=row, column=1, columnspan=2, sticky="ew")

    def _load_channel_exposure_controls(self):
        values = self.channel_exposure[self.current_channel]
        self._updating_exposure_controls = True
        try:
            self.black_exposure_var.set(values["black"])
            self.white_exposure_var.set(values["white"])
        finally:
            self._updating_exposure_controls = False

    def _on_black_exposure_changed(self, value):
        if self._updating_exposure_controls:
            return
        black = float(value)
        values = self.channel_exposure[self.current_channel]
        values["black"] = min(black, values["white"] - 1.0)
        if values["black"] != black:
            self._updating_exposure_controls = True
            try:
                self.black_exposure_var.set(values["black"])
            finally:
                self._updating_exposure_controls = False
        self._exposure_changed()

    def _on_white_exposure_changed(self, value):
        if self._updating_exposure_controls:
            return
        white = float(value)
        values = self.channel_exposure[self.current_channel]
        values["white"] = max(white, values["black"] + 1.0)
        if values["white"] != white:
            self._updating_exposure_controls = True
            try:
                self.white_exposure_var.set(values["white"])
            finally:
                self._updating_exposure_controls = False
        self._exposure_changed()

    def _exposure_changed(self):
        channel = self.current_channel
        self.resized_preview_cache = {
            key: image
            for key, image in self.resized_preview_cache.items()
            if key[1] != channel
        }
        self.schedule_render()

    def reset_channel_exposure(self):
        self.channel_exposure[self.current_channel] = {
            "black": OVERVIEW_EXPOSURE_BLACK_DEFAULT,
            "white": OVERVIEW_EXPOSURE_WHITE_DEFAULT,
        }
        self._load_channel_exposure_controls()
        self._exposure_changed()

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
            f"{selected_count} included  ·  {excluded_count} excluded    "
            f"{self.current_channel} channel  ·  "
            f"{loaded_count}/{len(self.ims_files)} ready  ·  "
            f"{cached_count}/{cache_target} cached  ·  "
            f"{self.zoom:.2f}x"
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
        return np.asarray(mip)

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
                mip = completed.result()
                payload = (item, mip, None)
            except BaseException as exc:
                payload = (item, None, str(exc))
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
                key, mip, error = self.events.get_nowait()
            except queue.Empty:
                break
            self.pending.discard(key)
            self.foreground_futures.pop(key, None)
            self.background_futures.pop(key, None)
            self.preview_cache[key] = {
                "mip": mip,
                "error": error,
            }
            changed = True
        if changed:
            self.schedule_render()
            self._update_status()
            if (
                not self.initial_previews_ready_notified
                and self.on_initial_previews_ready is not None
                and all(
                    (path, self.current_channel) in self.preview_cache
                    for path in self.ims_files
                )
            ):
                self.initial_previews_ready_notified = True
                self.on_initial_previews_ready()
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
                mip = entry["mip"]
                image_size = (int(mip.shape[1]), int(mip.shape[0]))
                fitted = self._fit_size(
                    image_size,
                    max(1, tile_width - 2 * border_width),
                    max(1, image_height - 2 * border_width),
                )
                exposure = self.channel_exposure[self.current_channel]
                black = float(exposure["black"])
                white = float(exposure["white"])
                resized_key = (
                    path,
                    self.current_channel,
                    fitted,
                    black,
                    white,
                )
                resized = self.resized_preview_cache.get(resized_key)
                if resized is None:
                    windowed = _apply_preview_exposure(mip, black, white)
                    u8 = (np.clip(windowed, 0.0, 1.0) * 255.0).astype(np.uint8)
                    image = self.Image.fromarray(u8, mode="L")
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
        self._load_channel_exposure_controls()
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


def choose_image_quality_overview(
    ims_files,
    input_dir,
    progress=None,
    on_initial_previews_ready=None,
):
    """Review the series, apply confirmed exclusions, and return included files."""
    if progress is not None:
        progress.update(
            "Opening the image-quality overview...",
            "Preparing high-resolution g-channel MIPs for the complete series.",
        )
        progress.close()

    review = ImageQualityOverviewWindow(
        ims_files,
        input_dir=input_dir,
        on_initial_previews_ready=on_initial_previews_ready,
    ).run()
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


# ============================================================================
# BEGIN GENERATED MODULE: gui.py
# ============================================================================

"""Tkinter exposure, landmark, channel, and custom-ROI interface."""
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


# ============================================================================
# BEGIN GENERATED MODULE: self_test.py
# ============================================================================

"""Non-interactive validation used for portable release testing."""

from datetime import datetime
import json
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import traceback


def run_self_test(report_path):
    report_path = Path(report_path).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "started": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "python": sys.version,
        "platform": platform.platform(),
        "checks": {},
    }

    try:
        import numpy
        import scipy
        from cellpose import models


        # Validate the actual Tcl/Tk runtime and image ownership used by the
        # startup windows. Importing tkinter alone does not detect a missing
        # Tcl library in a portable build.
        import tkinter as tk

        tk_root = tk.Tk()
        tk_root.withdraw()
        try:
            icon = tk.PhotoImage(master=tk_root, file=str(GUI_ICON_PATH))
            probe = tk.Label(tk_root, image=icon)
            probe.pack()
            tk_root.update_idletasks()
            report["checks"]["tk_window_and_image"] = True
            report["tcl_patchlevel"] = str(
                tk_root.tk.call("info", "patchlevel")
            )
        finally:
            tk_root.destroy()

        model_path = Path(CELLPOSE_MODEL_PATH)
        donor_path = Path(SCHEMA_DONOR_IMS)
        report["versions"] = {
            "h5py": h5py.__version__,
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "torch": torch.__version__,
            "torch_cuda_runtime": torch.version.cuda,
        }
        report["hardware"] = {
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_device": (
                torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
            ),
        }
        report["checks"]["custom_model_exists"] = model_path.is_file()
        report["checks"]["builtin_model_exists"] = (
            Path(models.MODEL_DIR) / "cpsam_v2"
        ).is_file()
        report["checks"]["donor_exists"] = donor_path.is_file()
        if donor_path.is_file():
            donor_valid, donor_reason = donor_has_required_groups(donor_path)
        else:
            donor_valid, donor_reason = False, "donor file is missing"
        report["checks"]["donor_schema_valid"] = bool(donor_valid)
        report["donor_validation"] = str(donor_reason)
        report["paths"] = {
            "custom_model": str(model_path),
            "cellpose_model_dir": str(models.MODEL_DIR),
            "donor": str(donor_path),
        }

        roi_points = numpy.asarray([[5.0, 5.0], [20.0, 20.0]])
        roi_polygon = numpy.asarray(
            [[0.0, 0.0], [0.0, 10.0], [10.0, 10.0], [10.0, 0.0]]
        )
        include_mask = custom_roi_keep_mask_yx(
            roi_points,
            roi_polygon,
            "include",
        )
        exclude_mask = custom_roi_keep_mask_yx(
            roi_points,
            roi_polygon,
            "exclude",
        )
        report["checks"]["inclusive_exclusion_roi"] = bool(
            numpy.array_equal(include_mask, numpy.asarray([True, False]))
            and numpy.array_equal(exclude_mask, numpy.asarray([False, True]))
        )

        if not all(report["checks"].values()):
            raise RuntimeError("One or more bundled resources failed validation.")

        # Exercise the Imaris ColorRange path used by real exports, including
        # the mapping from Neurodot's logical names to physical IMS channels.
        with tempfile.TemporaryDirectory(prefix="neurodot-self-test-") as temp_dir:
            viewer_path = Path(temp_dir) / "spot_viewer_metadata.ims"
            shutil.copy2(donor_path, viewer_path)
            with h5py.File(viewer_path, "r+") as viewer_file:
                for scene_name in ("Scene", "Scene8"):
                    scene_data = viewer_file[f"{scene_name}/Data"]
                    set_predicted_spot_rendering_in_scene_xml(scene_data)
                    xml = read_scene_xml(scene_data)
                    blocks = extract_points_viewers(xml)
                    for config in PREDICTED_GROUPS:
                        token = f'<bpPointsId Value="{int(config["id"])}"/>'
                        block = next(item for item in blocks if token in item)
                        assert 'mStyle="eCenterPoint"' in block
                        assert 'mRadiusScale="1"' in block
                        assert (
                            f'mCenterPointSize="{PREDICTED_CENTER_POINT_SIZE_PX}"'
                            in block
                        )
            report["checks"]["imaris_spot_size_metadata"] = True
            report["spot_display"] = {
                "diameter_um": float(PREDICTED_SPOT_DIAMETER_UM),
                "center_point_width_px": int(PREDICTED_CENTER_POINT_SIZE_PX),
            }

            metadata_path = Path(temp_dir) / "display_metadata.ims"
            expected_ranges = {
                "g": {"black": 207.15, "white": 771.742},
                "b": {"black": 124.0, "white": 1338.18},
                "r": {"black": 104.0, "white": 546.2},
                "405": {"black": 142.968, "white": 247.668},
            }
            channel_metadata = (
                ("405", "447"),
                ("g", "525"),
                ("r", "600"),
                ("b", "708"),
            )
            with h5py.File(metadata_path, "w") as metadata_file:
                dataset_info = metadata_file.create_group("DataSetInfo")
                for channel_index, (name, wavelength) in enumerate(channel_metadata):
                    channel_group = dataset_info.create_group(f"Channel {channel_index}")
                    channel_group.attrs["Name"] = numpy.frombuffer(
                        name.encode("ascii"), dtype="S1"
                    )
                    channel_group.attrs["EmissionWavelength"] = numpy.frombuffer(
                        wavelength.encode("ascii"), dtype="S1"
                    )
                write_imaris_channel_display_ranges(metadata_file, expected_ranges)
                validate_imaris_channel_display_ranges(metadata_file, expected_ranges)
            report["checks"]["imaris_display_metadata"] = True

        loaded = load_model(torch.device("cpu"))
        report["checks"]["custom_model_load"] = loaded is not None
        if loaded is None:
            raise RuntimeError("The bundled custom Cellpose model did not load.")

        report["status"] = "passed"
        report["finished"] = datetime.now().isoformat(timespec="seconds")
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return True
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        report["finished"] = datetime.now().isoformat(timespec="seconds")
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return False


# ============================================================================
# BEGIN GENERATED MODULE: workflow.py
# ============================================================================

"""Neurodot batch inference and Imaris export orchestration."""
# =============================================================================
# BATCH INFERENCE
# =============================================================================

def initialize_models(device, progress=None):
    """Load the selected Cellpose model once and share it across all channels."""
    pretrained_model, model_source = resolve_cellpose_pretrained_model()

    print("\n--- Loading Cellpose model ---")
    if model_source == "builtin":
        print(f"  Built-in model: {NATIVE_CELLPPOSE_MODEL}")
    else:
        print(f"  Local model file: {pretrained_model}")

    if progress is not None:
        progress.update(
            "Loading the Cellpose model...",
            "This is done once and the model is then shared by all channels.",
            heading="PREPARING CELLPOSE",
        )

    model_info = load_model(
        device
    )

    loaded = {
        name: model_info
        for name in CHANNEL_PROCESSING_ORDER
    }

    model_label = (
        NATIVE_CELLPPOSE_MODEL
        if model_source == "builtin"
        else Path(pretrained_model).name
    )

    for name in CHANNEL_PROCESSING_ORDER:
        print(
            f"  {name}: Cellpose {model_label} "
            "(shared model instance)"
        )

    return loaded

def predict_channel_spots_3d(
    volume_zyx,
    loaded_model,
    cfg,
    geo,
    channel_key,
    exposure,
):
    mip = np.max(
        volume_zyx,
        axis=0,
    )

    black = float(exposure["black"])
    white = float(exposure["white"])

    windowed = apply_manual_exposure(
        mip,
        black,
        white,
    )

    print(
        f"  Manual exposure: black={black:.3f}, white={white:.3f}"
    )

    zero_fraction = float(
        np.mean(windowed <= 0.0)
    )
    saturated_fraction = float(
        np.mean(windowed >= 1.0)
    )

    print(
        f"  Exact Cellpose input: "
        f"{zero_fraction * 100:.2f}% pixels at 0, "
        f"{saturated_fraction * 100:.2f}% pixels at 1"
    )

    masks, centroids_yx, areas = run_windowed_cellpose_instances(
        loaded_model,
        windowed,
        cfg,
    )

    print(
        f"  Cellpose segmented instances: {len(centroids_yx)}"
    )

    if len(areas):
        print(
            "  Instance area px: "
            f"median={np.median(areas):.1f}, "
            f"min={np.min(areas)}, max={np.max(areas)}"
        )

    if len(centroids_yx) == 0:
        return (
            np.empty((0, 3), dtype=np.float32),
            centroids_yx,
            np.empty((0,), dtype=np.float32),
            areas,
        )

    z_indices = choose_z_indices(
        volume_zyx=volume_zyx,
        centroids_yx=centroids_yx,
        cfg=cfg,
        geo=geo,
    )

    # Sanity check: every detector centroid must live inside the logical
    # Imaris pixel domain used for physical-coordinate conversion.
    if len(
        centroids_yx
    ):
        cy = centroids_yx[
            :,
            0
        ]
        cx = centroids_yx[
            :,
            1
        ]

        if (
            np.any(
                cx < -0.5
            )
            or np.any(
                cx > geo["nx"] - 0.5
            )
            or np.any(
                cy < -0.5
            )
            or np.any(
                cy > geo["ny"] - 0.5
            )
        ):
            raise RuntimeError(
                "Cellpose centroid lies outside logical Imaris X/Y bounds. "
                "This indicates a storage/logical coordinate mismatch."
            )

    xyz = detector_coordinates_to_imaris_xyz(
        centroids_yx,
        z_indices,
        geo,
    )

    return (
        xyz,
        centroids_yx,
        z_indices,
        areas,
    )



def predict_all_groups(
    ims_path,
    loaded_models,
    device,
    exposure_settings,
    manual_landmarks_yx,
    enabled_channels=None,
    counting_regions=None,
    custom_rois_yx=None,
    custom_roi_modes=None,
    progress=None,
    file_position=None,
    file_total=None,
):
    """Run inference without modifying the source file."""
    predictions = {
        name: np.empty((0, 3), dtype=np.float32)
        for name in CHANNEL_PROCESSING_ORDER
    }

    if enabled_channels is None:
        enabled_channels = set(CHANNEL_PROCESSING_ORDER)
    else:
        enabled_channels = {
            str(channel)
            for channel in enabled_channels
            if str(channel) in CHANNEL_PROCESSING_ORDER
        }

    with h5py.File(ims_path, "r") as h5:
        geo = get_image_geometry(
            h5,
            verbose=True,
        )

        if str(Z_PLACEMENT_MODE).strip().lower() == "stack_center":
            z_center_um = (
                (geo["min_z"] + geo["max_z"]) / 2.0
                + float(Z_CENTER_OFFSET_UM)
            )
            z_center_um = float(
                np.clip(
                    z_center_um,
                    geo["min_z"],
                    geo["max_z"],
                )
            )
            print(
                f"  All generated Spots will use centered Z = "
                f"{z_center_um:.6f} um"
            )

        channel_map = map_channels(
            h5,
            verbose=True,
        )

        print(
            f"Resolved channel map: {channel_map}"
        )

        for name in CHANNEL_PROCESSING_ORDER:
            if name not in enabled_channels:
                print(
                    f"\n[{name}] Disabled for this series -> skipping Cellpose; "
                    "export will receive placeholder Spot."
                )
                continue

            if name not in loaded_models:
                print(
                    f"\n[{name}] No loaded model -> empty group."
                )
                continue

            if name not in channel_map:
                print(
                    f"\n[{name}] No matching image channel -> empty group."
                )
                continue

            ch_idx = channel_map[name]
            dset_path = (
                "DataSet/ResolutionLevel 0/TimePoint 0/"
                f"Channel {ch_idx}/Data"
            )

            if dset_path not in h5:
                print(
                    f"\n[{name}] Missing {dset_path} -> empty group."
                )
                continue

            if progress is not None:
                progress.update(
                    f"Detecting cells in channel {name}",
                    f"File {file_position} of {file_total}: {Path(ims_path).name}",
                    current=file_position - 1 if file_position else None,
                    total=file_total,
                    heading="COUNTING CELLS",
                )

            active_model = loaded_models[name].get(
                "pretrained_model",
                NATIVE_CELLPPOSE_MODEL,
            )
            active_model_label = (
                NATIVE_CELLPPOSE_MODEL
                if active_model == NATIVE_CELLPPOSE_MODEL
                else Path(str(active_model)).name
            )

            print(
                f"\n--- Detecting {name} on Channel {ch_idx} "
                f"with Cellpose {active_model_label} ---"
            )

            logical_shape = (
                get_imaris_logical_shape_zyx(
                    h5
                )
            )

            volume = np.asarray(
                h5[
                    dset_path
                ][:]
            )

            raw_storage_shape = tuple(
                volume.shape
            )

            volume = (
                crop_volume_to_imaris_logical_shape(
                    volume,
                    logical_shape,
                )
            )

            if (
                tuple(
                    volume.shape
                )
                != raw_storage_shape
            ):
                print(
                    "  Cropped padded HDF5 volume: "
                    f"{raw_storage_shape} -> {tuple(volume.shape)}"
                )

            (
                xyz,
                centroids_yx,
                z_indices,
                areas,
            ) = predict_channel_spots_3d(
                volume_zyx=volume,
                loaded_model=loaded_models[name],
                cfg=SPOT_SETTINGS[name],
                geo=geo,
                channel_key=name,
                exposure=exposure_settings[name],
            )

            predictions[name] = xyz

            print(
                f"Detected {len(xyz)} spots for {name!r}."
            )

            for i in range(min(5, len(xyz))):
                cy, cx = centroids_yx[i]
                zi = z_indices[i]
                x, y, z = xyz[i]
                print(
                    f"  {i:3d}: Cellpose centroid(y,x)="
                    f"({cy:.2f},{cx:.2f}) -> z={zi:.2f} -> "
                    f"Imaris XYZ=({x:.3f}, {y:.3f}, {z:.3f}) um"
                )

            del volume

        all_landmarks_xyz = manual_landmarks_yx_to_imaris_xyz(
            h5,
            manual_landmarks_yx,
        )

        for key, xyz in all_landmarks_xyz.items():
            print(
                f"Manual {key}: "
                f"XYZ=({xyz[0,0]:.3f}, "
                f"{xyz[0,1]:.3f}, "
                f"{xyz[0,2]:.3f}) um"
            )

        rotation_info = compute_rotation_info(
            manual_landmarks_yx
        )
        print(
            "Midline rotation (counterclockwise to vertical): "
            f"{rotation_info['ccw_deg']:.2f} deg -> "
            f"{rotation_info['group_name']}"
        )

        split_predictions, split_counts = split_predictions_by_midline(
            predictions,
            manual_landmarks_yx,
            h5,
        )
        print("Midline-based hemisphere split (L / R / on-line):")
        for name in CHANNEL_PROCESSING_ORDER:
            nl, nr, no = split_counts[name]
            print(f"  {name:>3}: {nl} / {nr} / {no}")

        split_predictions, roi_counts = filter_split_predictions_to_counting_rectangles(
            split_predictions,
            manual_landmarks_yx,
            h5,
            counting_regions=counting_regions,
            custom_rois_yx=custom_rois_yx,
            custom_roi_modes=custom_roi_modes,
        )
        print(
            "Channel-specific landmark counting-region filter "
            f"(margin={COUNTING_ROI_MARGIN_PX:.0f} px; before -> kept):"
        )
        for name in CHANNEL_PROCESSING_ORDER:
            l_before, l_kept = roi_counts["L"][name]
            r_before, r_kept = roi_counts["R"][name]
            region = (
                counting_regions.get(name, DEFAULT_COUNTING_REGION)
                if isinstance(counting_regions, dict)
                else DEFAULT_COUNTING_REGION
            )
            channel_custom_roi = (custom_rois_yx or {}).get(name)
            if isinstance(channel_custom_roi, dict):
                custom_sides = [
                    hemi
                    for hemi in ("L", "R")
                    if len(channel_custom_roi.get(hemi, []))
                    >= CUSTOM_ROI_MIN_VERTICES
                ]
            elif (
                channel_custom_roi is not None
                and len(channel_custom_roi) >= CUSTOM_ROI_MIN_VERTICES
            ):
                custom_sides = ["L", "R"]
            else:
                custom_sides = []
            custom_label = (
                " + custom ROI " + "/".join(
                    f"{hemi}:{str((custom_roi_modes or {}).get(name, {}).get(hemi, DEFAULT_CUSTOM_ROI_MODE))}"
                    if isinstance((custom_roi_modes or {}).get(name, {}), dict)
                    else hemi
                    for hemi in custom_sides
                )
                if custom_sides
                else ""
            )
            print(
                f"  {name:>3} [{region}{custom_label}]: "
                f"L {l_before}->{l_kept}  "
                f"R {r_before}->{r_kept}"
            )

    return predictions, split_predictions, all_landmarks_xyz, rotation_info



def add_empty_predicted_group_placeholders(
    ims_path,
    hemisphere_predictions,
    manual_landmarks_yx,
    hemisphere,
):
    """Place distinct empty-group placeholders near si and inside the ROI.

    This is applied only at output-writing time. It does not affect Cellpose
    detection, the reported real counts, or the midline-based L/R split.

    Candidate positions form a physical-XY lattice around ``si``. Only points
    inside this hemisphere's exact landmark rectangle and image bounds are
    eligible. Every placeholder is at least ``PLACEHOLDER_SPACING_UM`` from
    other placeholders and conservatively from real predicted Spots, avoiding
    the downstream 3.5 um colocalization rule.
    """
    hemisphere = str(hemisphere).upper()
    if hemisphere not in ("L", "R"):
        raise ValueError(f"Unknown hemisphere: {hemisphere!r}")

    si_xyz = normalize_xyz(
        hemisphere_predictions.get(
            "si",
            np.empty((0, 3), dtype=np.float32),
        )
    )

    if len(si_xyz) == 0:
        raise RuntimeError(
            "Cannot create empty-group placeholder because the output si "
            "landmark is missing."
        )

    empty_groups = []
    occupied_xyz = []
    for group_name in CHANNEL_PROCESSING_ORDER:
        xyz = normalize_xyz(
            hemisphere_predictions.get(
                group_name,
                np.empty((0, 3), dtype=np.float32),
            )
        )
        if len(xyz) == 0:
            empty_groups.append(group_name)
        else:
            occupied_xyz.extend(xyz.astype(np.float64))

    if not empty_groups:
        return []

    spacing_um = float(PLACEHOLDER_SPACING_UM)
    if spacing_um <= float(PLACEHOLDER_COLOCALIZATION_THRESHOLD_UM):
        raise RuntimeError(
            "PLACEHOLDER_SPACING_UM must exceed the downstream "
            "colocalization threshold."
        )

    with h5py.File(ims_path, "r") as h5:
        geo = get_image_geometry(
            h5,
            verbose=False,
        )

    x_span = float(geo["max_x"] - geo["min_x"])
    y_span = float(geo["max_y"] - geo["min_y"])
    if x_span <= 0.0 or y_span <= 0.0:
        raise RuntimeError("Invalid image extent while placing placeholders.")

    si = si_xyz[0].astype(np.float64, copy=True)
    selected = []
    # Searching by successive square rings makes the result deterministic and
    # keeps selected positions as close to si as the constraints allow.
    max_rings = max(
        4,
        int(math.ceil(max(x_span, y_span) / spacing_um)) + 1,
    )

    for ring in range(1, max_rings + 1):
        offsets = []
        for iy in range(-ring, ring + 1):
            for ix in range(-ring, ring + 1):
                if max(abs(ix), abs(iy)) != ring:
                    continue
                offsets.append((
                    math.hypot(ix, iy),
                    ix,
                    iy,
                ))
        offsets.sort(key=lambda item: (item[0], item[2], item[1]))

        for _distance, ix, iy in offsets:
            candidate = si.copy()
            candidate[0] += float(ix) * spacing_um
            candidate[1] += float(iy) * spacing_um

            if not (
                geo["min_x"] <= candidate[0] <= geo["max_x"]
                and geo["min_y"] <= candidate[1] <= geo["max_y"]
                and geo["min_z"] <= candidate[2] <= geo["max_z"]
            ):
                continue

            px = (
                (candidate[0] - geo["min_x"]) / x_span
            ) * float(geo["nx"]) - 0.5
            py = (
                (candidate[1] - geo["min_y"]) / y_span
            ) * float(geo["ny"]) - 0.5
            inside = counting_rectangle_mask_yx(
                np.asarray([[py, px]], dtype=np.float64),
                manual_landmarks_yx,
                hemisphere,
                margin_px=0.0,
                counting_region="whole",
            )[0]
            if not bool(inside):
                continue

            all_occupied = occupied_xyz + selected
            if all_occupied:
                distances = np.linalg.norm(
                    np.asarray(all_occupied, dtype=np.float64)[:, :2]
                    - candidate[None, :2],
                    axis=1,
                )
                if np.any(distances < spacing_um - 1e-6):
                    continue

            selected.append(candidate)
            if len(selected) == len(empty_groups):
                break

        if len(selected) == len(empty_groups):
            break

    if len(selected) < len(empty_groups):
        raise RuntimeError(
            f"Could not place {len(empty_groups)} distinct placeholder Spots "
            f"inside the {hemisphere} counting rectangle with "
            f"{spacing_um:.1f} um spacing."
        )

    added = []
    for group_name, placeholder in zip(empty_groups, selected):
        hemisphere_predictions[group_name] = np.asarray(
            [placeholder],
            dtype=np.float32,
        )
        added.append(group_name)
        print(
            f"  Placeholder {group_name}/{hemisphere}: "
            f"XYZ=({placeholder[0]:.3f}, {placeholder[1]:.3f}, "
            f"{placeholder[2]:.3f}) um"
        )

    return added

def process_single_ims_file(
    ims_path,
    loaded_models,
    device,
    schema_donor_ims,
    exposure_settings,
    manual_landmarks_yx,
    enabled_channels=None,
    counting_regions=None,
    custom_rois_yx=None,
    custom_roi_modes=None,
    progress=None,
    file_position=None,
    file_total=None,
):
    print("\n" + "=" * 72)
    print(f"PROCESSING: {ims_path.name}")
    print("=" * 72)

    # Expensive detection happens ONCE.
    (
        predictions,
        split_predictions,
        all_landmarks_xyz,
        rotation_info,
    ) = predict_all_groups(
        ims_path=ims_path,
        loaded_models=loaded_models,
        device=device,
        exposure_settings=exposure_settings,
        manual_landmarks_yx=manual_landmarks_yx,
        enabled_channels=enabled_channels,
        counting_regions=counting_regions,
        custom_rois_yx=custom_rois_yx,
        custom_roi_modes=custom_roi_modes,
        progress=progress,
        file_position=file_position,
        file_total=file_total,
    )

    outputs = {}

    for hemisphere in ("L", "R"):
        if progress is not None:
            progress.update(
                f"Writing {hemisphere} hemisphere output",
                f"File {file_position} of {file_total}: {Path(ims_path).name}",
                current=file_position - 1 if file_position else None,
                total=file_total,
                heading="CREATING IMARIS FILES",
            )
        hemisphere_predictions = {
            key: value
            for key, value in split_predictions[hemisphere].items()
        }

        # Each file receives only the Cellpose spots on its own side of the
        # directed anatomical midline. The manual ce landmark is shared;
        # si/bo/to remain hemisphere-specific.
        hemisphere_predictions.update(
            hemisphere_manual_predictions(
                all_landmarks_xyz,
                hemisphere,
            )
        )

        placeholder_groups = add_empty_predicted_group_placeholders(
            ims_path,
            hemisphere_predictions,
            manual_landmarks_yx,
            hemisphere,
        )
        if placeholder_groups:
            print(
                "  Added si-adjacent placeholder Spot for empty predicted "
                "group(s): " + ", ".join(placeholder_groups)
            )

        output_path = (
            OUTPUT_SCENE_DIR
            / f"{ims_path.stem}{OUTPUT_FILE_TAG}_{hemisphere}.ims"
        )

        print(
            f"\n--- WRITING {hemisphere} LANDMARK OUTPUT ---"
        )

        populate_ims_scene(
            input_ims=ims_path,
            schema_donor_ims=schema_donor_ims,
            output_ims=output_path,
            predictions=hemisphere_predictions,
            rotation_group_name=rotation_info[
                "group_name"
            ],
            display_exposure_settings=exposure_settings,
        )

        outputs[hemisphere] = output_path

        print(
            f"Output {hemisphere}: {output_path.resolve()}"
        )

    print("\nOriginal unsplit Cellpose counts:")
    for name in CHANNEL_PROCESSING_ORDER:
        print(
            f"  {name:>3}: {len(predictions[name])}"
        )

    print("Split Cellpose counts by hemisphere:")
    for name in CHANNEL_PROCESSING_ORDER:
        print(
            f"  {name:>3}: L={len(split_predictions['L'][name])}  "
            f"R={len(split_predictions['R'][name])}"
        )

    print(
        "Manual outputs: L/R contain only their own-side Cellpose spots, "
        "their own si/bo/to, the same ce, and the same rotation metadata group "
        f"{rotation_info['group_name']}."
    )

    return outputs



def run_workflow(
    progress=None,
    use_quality_review=True,
    preselected_ims_files=None,
    preloaded_models=None,
    quality_review_completed=False,
):
    if progress is not None:
        progress.update(
            "Checking the selected folders...",
            "Looking for IMS files and validating the output template.",
        )
    IMS_INPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_SCENE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ims_files = (
        sorted(IMS_INPUT_DIR.glob("*.ims"))
        if preselected_ims_files is None
        else [Path(path) for path in preselected_ims_files]
    )
    configured_donor_resolved = SCHEMA_DONOR_IMS.resolve()
    ims_files = [
        p
        for p in ims_files
        if p.resolve() != configured_donor_resolved
    ]

    if not ims_files:
        print(
            f"No .ims files found in {IMS_INPUT_DIR.resolve()}"
        )
        if progress is not None:
            progress.finish(
                False,
                "No IMS files were found.",
                f"Add .ims files to:\n{IMS_INPUT_DIR.resolve()}",
                output_dir=IMS_INPUT_DIR,
            )
        return

    if use_quality_review:
        had_progress_window = progress is not None
        ims_files = choose_image_quality_overview(
            ims_files,
            input_dir=IMS_INPUT_DIR,
            progress=progress,
        )
        if ims_files is None:
            print(
                "Image-quality review cancelled by the user; "
                "no IMS files were moved or processed."
            )
            return None

        if had_progress_window:

            progress = ProgressWindow()
            progress.show(
                status="Preparing the selected IMS files...",
                detail=(
                    f"{len(ims_files)} file(s) passed image-quality review. "
                    "The output template and Cellpose model will be checked next."
                ),
                heading="PREPARING CELL COUNTING",
            )
    elif quality_review_completed:
        print("Image-quality review completed before workflow initialization.")
        if progress is not None:
            progress.update(
                "Preparing the selected IMS files...",
                f"Using {len(ims_files)} file(s) accepted during image QC.",
                heading="PREPARING CELL COUNTING",
            )
    else:
        print("Image-quality review skipped by the user.")
        if progress is not None:
            progress.update(
                "Preparing the IMS files...",
                (
                    f"Image QC was skipped. Checking the output template and "
                    f"Cellpose model for {len(ims_files)} file(s)."
                ),
                heading="PREPARING CELL COUNTING",
            )

    if not SCHEMA_DONOR_IMS.exists():
        raise FileNotFoundError(
            "Schema donor not found:\n"
            f"  {SCHEMA_DONOR_IMS.resolve()}\n"
            "Use the whole manually annotated .ims file containing "
            "valid g, b, r and 405 groups."
        )

    schema_donor_ims = resolve_schema_donor(
        SCHEMA_DONOR_IMS
    )

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    hardware = (
        torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else "CPU"
    )

    print(
        "\n--- Manual-exposure Cellpose workflow ---"
    )
    print(
        "  Manual black/white window: ON"
    )
    print(
        "  Cellpose internal normalization / auto-exposure: OFF"
    )
    print(
        "  Candidate-population fluorescence gate: OFF"
    )
    print(
        "  Fluorescence XY recentering: OFF"
    )
    print(
        "  Candidates: actual Cellpose instance masks"
    )
    print(
        f"  Cellpose cellprob threshold: "
        f"{WINDOWED_CELLPOSE_CELLPROB_THRESHOLD:.2f}"
    )
    print(
        f"  Cellpose flow threshold: "
        f"{WINDOWED_CELLPOSE_FLOW_THRESHOLD:.2f}"
    )

    print(f"Hardware: {hardware}")
    print(f"Files: {len(ims_files)}")
    print(f"Schema donor: {schema_donor_ims.resolve()}")
    print(f"Output file tag: {OUTPUT_FILE_TAG!r}")
    print(
        f"Imaris Spot diameter: {PREDICTED_SPOT_DIAMETER_UM:g} um "
        f"(radius {PREDICTED_SPOT_RADIUS_UM:g} um)"
    )

    configured_model, configured_model_source = resolve_cellpose_pretrained_model()
    if configured_model_source == "builtin":
        print(f"Cellpose model: built-in {NATIVE_CELLPPOSE_MODEL}")
    else:
        print(f"Cellpose model: local file {configured_model}")

    print(f"Z placement mode: {Z_PLACEMENT_MODE}")

    if Z_PLACEMENT_MODE == "stack_center":
        print(
            f"Z center offset: {Z_CENTER_OFFSET_UM:+.3f} um "
            "(all spots will share the stack midpoint Z)"
        )

    if preloaded_models is not None:
        loaded_models = preloaded_models
        if progress is not None:
            progress.update(
                "Cellpose is ready.",
                "The model was loaded in the background during image QC.",
                heading="PREPARING CELL COUNTING",
            )
    elif progress is not None:
        loaded_models = progress.run_task(
            lambda: initialize_models(device, progress=progress)
        )
    else:
        loaded_models = initialize_models(device)

    if not loaded_models:
        raise RuntimeError(
            "The native Cellpose model could not be loaded."
        )

    # GUI appears ONCE for the complete series before any production Cellpose
    # inference is performed. Test Cellpose is optional inside the GUI.
    selection = choose_batch_exposure_settings(
        ims_files=ims_files,
        loaded_models=loaded_models,
        progress=progress,
    )

    if selection is None:
        print("Counting run cancelled by the user; no IMS files were modified.")
        return None

    if progress is not None:
        # The pre-GUI progress root is deliberately destroyed before the main
        # Tk interface is created. Start a fresh root for batch progress after
        # that interface has closed.

        progress = ProgressWindow()
        progress.show(
            status="Saving the selected settings...",
            detail="Cell counting will start immediately afterwards.",
            heading="STARTING COUNTING RUN",
        )

    enabled_channels = list(
        selection.get(
            "enabled_channels",
            CHANNEL_PROCESSING_ORDER,
        )
    )

    selected_counting_regions = selection.get("counting_regions", {})
    counting_regions = {}
    for channel in CHANNEL_PROCESSING_ORDER:
        region = str(
            selected_counting_regions.get(channel, DEFAULT_COUNTING_REGION)
        ).strip().lower()
        if region not in COUNTING_REGION_MODES:
            raise RuntimeError(
                f"Invalid counting region for {channel}: {region!r}"
            )
        counting_regions[channel] = region

    custom_counting_rois_by_file = selection.get(
        "custom_counting_rois_yx",
        {},
    )
    custom_counting_roi_modes_by_file = selection.get(
        "custom_counting_roi_modes",
        {},
    )

    print(
        "\n--- Series-wide channel counting ---"
    )
    for channel in CHANNEL_PROCESSING_ORDER:
        print(
            f"  {channel:>3}: "
            + ("COUNT" if channel in enabled_channels else "SKIP -> placeholder only")
        )

    print("Channel-specific counting regions:")
    for channel in CHANNEL_PROCESSING_ORDER:
        print(f"  {channel:>3}: {counting_regions[channel].upper()}")

    print(
        "\n--- Series-average exposure settings ---"
    )

    for channel in CHANNEL_PROCESSING_ORDER:
        values = selection[
            "series_average"
        ][
            channel
        ]

        print(
            f"  {channel:>3}: "
            f"black={values['black']:.3f}, "
            f"white={values['white']:.3f}"
        )

    _save_exposure_settings(
        selection,
        ims_files,
    )

    failures = []

    for file_position, ims_path in enumerate(ims_files, start=1):
        try:
            file_exposure = selection[
                "per_file"
            ][
                ims_path.name
            ]

            file_landmarks = selection[
                "manual_landmarks_yx"
            ][
                ims_path.name
            ]

            file_custom_rois = custom_counting_rois_by_file.get(
                ims_path.name,
                {},
            )
            file_custom_roi_modes = custom_counting_roi_modes_by_file.get(
                ims_path.name,
                {},
            )

            print(
                "\nResolved exposure for this image:"
            )

            for channel in CHANNEL_PROCESSING_ORDER:
                values = file_exposure[
                    channel
                ]

                print(
                    f"  {channel:>3}: "
                    f"black={values['black']:.3f}, "
                    f"white={values['white']:.3f} "
                    f"({values['source']})"
                )

            processing_arguments = dict(
                ims_path=ims_path,
                loaded_models=loaded_models,
                device=device,
                schema_donor_ims=schema_donor_ims,
                exposure_settings=file_exposure,
                manual_landmarks_yx=file_landmarks,
                enabled_channels=enabled_channels,
                counting_regions=counting_regions,
                custom_rois_yx=file_custom_rois,
                custom_roi_modes=file_custom_roi_modes,
                progress=progress,
                file_position=file_position,
                file_total=len(ims_files),
            )
            if progress is not None:
                progress.run_task(
                    lambda: process_single_ims_file(**processing_arguments)
                )
            else:
                process_single_ims_file(**processing_arguments)

        except Exception as exc:
            failures.append(
                (
                    ims_path.name,
                    str(exc),
                )
            )

            print(
                f"\n[ERROR] {ims_path.name}: {exc}"
            )
            print("\nFull traceback:")
            traceback.print_exc()

        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    print("\n" + "=" * 72)
    print("STEP 4 FINISHED")
    print("=" * 72)

    if failures:
        print(
            f"{len(failures)} file(s) failed:"
        )
        for filename, error in failures:
            print(
                f"  - {filename}: {error}"
            )
    else:
        print(
            "All files processed successfully."
        )

    if progress is not None:
        output_count = len(ims_files) * 2 - len(failures) * 2
        if failures:
            failed_names = ", ".join(name for name, _error in failures)
            progress.finish(
                False,
                f"Created {output_count} output file(s); {len(failures)} input file(s) failed.",
                f"Failed: {failed_names}\nOutput folder: {OUTPUT_SCENE_DIR.resolve()}",
                output_dir=OUTPUT_SCENE_DIR,
            )
        else:
            progress.finish(
                True,
                f"Successfully created {output_count} Imaris output files.",
                f"Saved to:\n{OUTPUT_SCENE_DIR.resolve()}",
                output_dir=OUTPUT_SCENE_DIR,
            )


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
            f"Add .ims files to:\n\n{IMS_INPUT_DIR.resolve()}",
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
