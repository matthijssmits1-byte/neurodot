"""Exposure processing and Cellpose instance detection."""
from .common import *
from .config import *
from .image_io import *
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




__all__ = [name for name in globals() if not name.startswith("__")]
