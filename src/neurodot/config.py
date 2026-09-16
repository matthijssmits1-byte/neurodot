"""Application configuration and stable defaults."""
from pathlib import Path
import math
import warnings

from .paths import (
    PROJECT_ROOT,
    RUNTIME_DATA_ROOT,
    configure_windows_app_identity,
    resolve_resource,
)
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


__all__ = [name for name in globals() if not name.startswith("__")]
