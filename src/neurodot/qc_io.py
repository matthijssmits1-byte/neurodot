"""Lightweight Imaris pyramid reading used before Cellpose is imported."""

import math
import re

import h5py
import numpy as np

from .config import CHANNEL_WAVELENGTH_BANDS_NM, TARGET_CONFIG


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


__all__ = ["choose_qc_resolution_level", "read_qc_mip_for_file_channel"]
