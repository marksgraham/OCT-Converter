"""Height Map Segmentation helpers for E2E layer contours.

Converts Heidelberg contour arrays into Height Map Segmentation frames
and maps layer IDs to CID 4273 Retinal Segmentation Surface codes.
"""

from __future__ import annotations

import re
import typing as t
from dataclasses import dataclass

import numpy as np

# Float padding must fall outside [0, OPT.Rows] (PS3.3 C.8.20.5.1).
HEIGHTMAP_PADDING_VALUE = -1.0

# Heidelberg layer id -> short name (eyepy SEG_MAPPING convention).
HEIDELBERG_LAYER_NAMES: dict[int, str] = {
    0: "ILM",
    1: "BM",
    2: "RNFL",
    3: "GCL",
    4: "IPL",
    5: "INL",
    6: "OPL",
    7: "ONL",
    8: "ELM",
    9: "IOS",
    10: "OPT",
    11: "CHO",
    12: "VIT",
    13: "ANT",
    14: "PR1",
    15: "PR2",
    16: "RPE",
    17: "IPL+",
    18: "IPL-",
}

# CID 4273 Retinal Segmentation Surface (coding scheme, value, meaning).
_CID4273: dict[int, tuple[str, str, str]] = {
    0: ("SCT", "280677004", "ILM - Internal limiting membrane"),
    1: ("DCM", "128300", "Outer surface of Bruch's Membrane"),
    2: ("DCM", "128289", "Outer surface of RNFL"),
    3: ("DCM", "128290", "Outer surface of GCL"),
    4: ("DCM", "128291", "Outer surface of IPL"),
    5: ("DCM", "128292", "Outer surface of INL"),
    6: ("DCM", "128293", "Outer surface of OPL"),
    8: ("SCT", "76710003", "ELM - External limiting membrane"),
    16: ("DCM", "128298", "Surface of the center of the RPE"),
}

# BCID 7150 Segmentation Property Categories
ANATOMICAL_STRUCTURE_CATEGORY = ("SRT", "T-D0050", "Anatomical Structure")

# Fallback for unmapped Heidelberg layer IDs
_GENERIC_PROPERTY_TYPE = ("OCT-converter", "L-0001", "Unspecified retinal surface")


@dataclass(frozen=True)
class LayerCode:
    """DICOM coded concept for a segmented retinal surface."""

    layer_id: int
    label: str
    category_scheme: str
    category_value: str
    category_meaning: str
    type_scheme: str
    type_value: str
    type_meaning: str


@dataclass
class HeightmapLayer:
    """One heightmap frame ready for Height Map Segmentation encoding."""

    layer_id: int
    code: LayerCode
    data: np.ndarray  # float32, shape (num_bscans, width)


def parse_contour_id(contour_key: str) -> int | None:
    """Extract numeric Heidelberg layer id from keys like ``contour0``."""
    match = re.fullmatch(r"contour(\d+)", contour_key)
    if match:
        return int(match.group(1))
    return None


def layer_code_for_id(layer_id: int) -> LayerCode:
    """Map a Heidelberg contour id to CID 4273 (or a generic fallback)."""
    label = HEIDELBERG_LAYER_NAMES.get(layer_id, f"contour{layer_id}")
    cat_scheme, cat_value, cat_meaning = ANATOMICAL_STRUCTURE_CATEGORY
    if layer_id in _CID4273:
        type_scheme, type_value, type_meaning = _CID4273[layer_id]
    else:
        type_scheme, type_value, type_meaning = _GENERIC_PROPERTY_TYPE
        type_meaning = f"Unspecified retinal surface ({label})"
    return LayerCode(
        layer_id=layer_id,
        label=label,
        category_scheme=cat_scheme,
        category_value=cat_value,
        category_meaning=cat_meaning,
        type_scheme=type_scheme,
        type_value=type_value,
        type_meaning=type_meaning,
    )


def contours_to_heightmaps(
    contours: dict,
    num_bscans: int,
    width: int,
    padding_value: float = HEIGHTMAP_PADDING_VALUE,
) -> list[HeightmapLayer]:
    """Convert E2E ``OCTVolumeWithMetaData.contours`` into heightmap layers.

    Args:
        contours: Mapping of ``contour{id}`` -> list of length ``num_bscans``,
            each entry a 1-D float array of length ``width`` or ``None``.
        num_bscans: Number of OPT B-scan frames (heightmap rows).
        width: Number of A-scan columns (must match OPT Columns).
        padding_value: Value for missing / invalid samples (outside [0, OPT.Rows]).

    Returns:
        List of HeightmapLayer sorted by layer id. Empty if no usable contours.
    """
    if not contours:
        return []

    layers: list[HeightmapLayer] = []
    for key in sorted(contours.keys(), key=_contour_sort_key):
        layer_id = parse_contour_id(key)
        if layer_id is None:
            continue
        slice_list = contours[key]
        heightmap = np.full((num_bscans, width), padding_value, dtype=np.float32)
        for i in range(num_bscans):
            if i >= len(slice_list):
                break
            contour = slice_list[i]
            if contour is None:
                continue
            arr = np.asarray(contour, dtype=np.float32)
            n = min(width, arr.shape[0])
            row = np.full(width, padding_value, dtype=np.float32)
            row[:n] = arr[:n]
            invalid = ~np.isfinite(row) | (row < 0)
            row[invalid] = padding_value
            heightmap[i] = row
        layers.append(
            HeightmapLayer(
                layer_id=layer_id,
                code=layer_code_for_id(layer_id),
                data=heightmap,
            )
        )
    return layers


def _contour_sort_key(key: str) -> t.Tuple[int, str]:
    layer_id = parse_contour_id(key)
    return (layer_id if layer_id is not None else 10**9, key)
