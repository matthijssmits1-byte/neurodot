"""Resolution-safe Imaris image reading, channel mapping, and rotation helpers."""
from .common import *
from .config import *
from .imaris_io import *
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



__all__ = [name for name in globals() if not name.startswith("__")]
