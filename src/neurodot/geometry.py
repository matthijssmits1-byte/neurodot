"""Landmark, Z-coordinate, hemisphere, rectangle, and ROI geometry."""
from .common import *
from .config import *
from .image_io import *
from .detection import *
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
        # Backward compatibility with the early v19 single-region form.
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



__all__ = [name for name in globals() if not name.startswith("__")]
