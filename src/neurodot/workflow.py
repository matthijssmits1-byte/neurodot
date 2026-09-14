"""Neurodot batch inference and Imaris export orchestration."""
from .common import *
from .config import *
from .imaris_io import *
from .image_io import *
from .detection import *
from .geometry import *
from .gui import *
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



def main(progress=None):
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

    if not SCHEMA_DONOR_IMS.exists():
        raise FileNotFoundError(
            "Schema donor not found:\n"
            f"  {SCHEMA_DONOR_IMS.resolve()}\n"
            "Use the whole manually annotated .ims file containing "
            "valid g, b, r and 405 groups."
        )

    ims_files = sorted(
        IMS_INPUT_DIR.glob("*.ims")
    )

    schema_donor_ims = resolve_schema_donor(
        SCHEMA_DONOR_IMS
    )

    donor_resolved = schema_donor_ims.resolve()

    ims_files = [
        p
        for p in ims_files
        if p.resolve() != donor_resolved
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

    if progress is not None:
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
        from .progress_gui import ProgressWindow

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

__all__ = [name for name in globals() if not name.startswith("__")]
