"""Imaris HDF5 scene writing, metadata synchronization, and validation."""
from .common import *
from .config import *
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
    from .image_io import map_channels

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

    from .image_io import map_channels

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
    # at module-import time while preserving v21's final geometry definition.
    from .image_io import get_image_geometry

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



__all__ = [name for name in globals() if not name.startswith("__")]
