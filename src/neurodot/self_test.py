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
        import h5py
        import numpy
        import scipy
        import torch
        from cellpose import models

        from .config import (
            CELLPOSE_MODEL_PATH,
            PREDICTED_CENTER_POINT_SIZE_PX,
            PREDICTED_GROUPS,
            PREDICTED_SPOT_DIAMETER_UM,
            SCHEMA_DONOR_IMS,
        )
        from .config import GUI_ICON_PATH
        from .detection import load_model
        from .geometry import custom_roi_keep_mask_yx
        from .imaris_io import (
            donor_has_required_groups,
            extract_points_viewers,
            read_scene_xml,
            set_predicted_spot_rendering_in_scene_xml,
            validate_imaris_channel_display_ranges,
            write_imaris_channel_display_ranges,
        )

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


__all__ = ["run_self_test"]
