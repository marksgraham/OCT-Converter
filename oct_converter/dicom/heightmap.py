"""Height Map Segmentation helpers for OCT layer contours.

Converts vendor contour arrays (Heidelberg E2E, Topcon FDA) into Height Map
Segmentation frames and maps surfaces to CID 4273 Retinal Segmentation
Surface codes.
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

# CID 4273 Retinal Segmentation Surface keyed by SegmentLabel.
# Values: (coding scheme, code value, code meaning).
SURFACE_CID4273: dict[str, tuple[str, str, str]] = {
    "ILM": ("SCT", "280677004", "ILM - Internal limiting membrane"),
    "BM": ("DCM", "128300", "Outer surface of Bruch's Membrane"),
    "RNFL": ("DCM", "128289", "Outer surface of RNFL"),
    "GCL": ("DCM", "128290", "Outer surface of GCL"),
    "IPL": ("DCM", "128291", "Outer surface of IPL"),
    "INL": ("DCM", "128292", "Outer surface of INL"),
    "OPL": ("DCM", "128293", "Outer surface of OPL"),
    "ELM": ("SCT", "76710003", "ELM - External limiting membrane"),
    "RPE": ("DCM", "128298", "Surface of the center of the RPE"),
}

# Topcon FDA contour key -> (SegmentLabel used for CID lookup / display).
# Composite boundary names map to the outer surface of the proximal layer.
TOPCON_LAYER_LABELS: dict[str, str] = {
    "ILM": "ILM",
    "RNFL_GCL": "RNFL",
    "GCL_IPL": "GCL",
    "IPL_INL": "IPL",
    "INL_OPL": "INL",
    "ELM": "ELM",
    "BM": "BM",
    "IZ_RPE": "RPE",
    # No exact CID 4273 match — SegmentLabel kept as source key; private fallback.
    "MZ_EZ": "MZ_EZ",
    "CSI": "CSI",
}

# Stable synthetic ids for Topcon layers (offset avoids Heidelberg id collisions).
_TOPCON_LAYER_IDS: dict[str, int] = {
    name: 1000 + i for i, name in enumerate(TOPCON_LAYER_LABELS)
}

# BCID 7150 Segmentation Property Categories
ANATOMICAL_STRUCTURE_CATEGORY = ("SRT", "T-D0050", "Anatomical Structure")

# Fallback for unmapped surface labels
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


def layer_code_for_label(label: str, layer_id: int) -> LayerCode:
    """Map a surface label to CID 4273 (or a generic fallback)."""
    cat_scheme, cat_value, cat_meaning = ANATOMICAL_STRUCTURE_CATEGORY
    if label in SURFACE_CID4273:
        type_scheme, type_value, type_meaning = SURFACE_CID4273[label]
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


def layer_code_for_id(layer_id: int) -> LayerCode:
    """Map a Heidelberg contour id to CID 4273 (or a generic fallback)."""
    label = HEIDELBERG_LAYER_NAMES.get(layer_id, f"contour{layer_id}")
    return layer_code_for_label(label, layer_id)


def contours_to_heightmaps(
    contours: dict,
    num_bscans: int,
    width: int,
    padding_value: float = HEIGHTMAP_PADDING_VALUE,
) -> list[HeightmapLayer]:
    """Convert ``OCTVolumeWithMetaData.contours`` into heightmap layers.

    Accepts both vendor schemas:

    * **E2E / Heidelberg:** ``contour{id}`` -> list of length ``num_bscans``,
      each entry a 1-D float array of length ``width`` or ``None``.
    * **FDA / Topcon:** named key (``ILM``, ``BM``, …) -> 2-D array of shape
      ``(n_bscans, width)`` with axial heights from the top of each B-scan.

    Args:
        contours: Contour mapping from an OCT volume.
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
        value = contours[key]
        heidelberg_id = parse_contour_id(key)

        if heidelberg_id is not None and _is_e2e_slice_list(value):
            heightmap = _heightmap_from_slice_list(
                value, num_bscans, width, padding_value
            )
            layers.append(
                HeightmapLayer(
                    layer_id=heidelberg_id,
                    code=layer_code_for_id(heidelberg_id),
                    data=heightmap,
                )
            )
            continue

        if _is_fda_heightmap(value):
            label = TOPCON_LAYER_LABELS.get(key, key)
            layer_id = _TOPCON_LAYER_IDS.get(key, 2000 + len(layers))
            heightmap = _heightmap_from_2d(value, num_bscans, width, padding_value)
            layers.append(
                HeightmapLayer(
                    layer_id=layer_id,
                    code=layer_code_for_label(label, layer_id),
                    data=heightmap,
                )
            )

    return layers


def _is_e2e_slice_list(value: t.Any) -> bool:
    if isinstance(value, np.ndarray) and value.ndim == 2:
        return False
    if not isinstance(value, (list, tuple)):
        return False
    return True


def _is_fda_heightmap(value: t.Any) -> bool:
    arr = np.asarray(value) if not isinstance(value, np.ndarray) else value
    return isinstance(arr, np.ndarray) and arr.ndim == 2


def _heightmap_from_slice_list(
    slice_list: t.Sequence,
    num_bscans: int,
    width: int,
    padding_value: float,
) -> np.ndarray:
    heightmap = np.full((num_bscans, width), padding_value, dtype=np.float32)
    for i in range(num_bscans):
        if i >= len(slice_list):
            break
        contour = slice_list[i]
        if contour is None:
            continue
        arr = np.asarray(contour, dtype=np.float32)
        if arr.ndim != 1:
            continue
        n = min(width, arr.shape[0])
        row = np.full(width, padding_value, dtype=np.float32)
        row[:n] = arr[:n]
        invalid = ~np.isfinite(row) | (row < 0)
        row[invalid] = padding_value
        heightmap[i] = row
    return heightmap


def _heightmap_from_2d(
    array: np.ndarray,
    num_bscans: int,
    width: int,
    padding_value: float,
) -> np.ndarray:
    arr = np.asarray(array, dtype=np.float32)
    heightmap = np.full((num_bscans, width), padding_value, dtype=np.float32)
    n_rows = min(num_bscans, arr.shape[0])
    n_cols = min(width, arr.shape[1])
    block = arr[:n_rows, :n_cols].copy()
    invalid = ~np.isfinite(block) | (block < 0)
    block[invalid] = padding_value
    heightmap[:n_rows, :n_cols] = block
    return heightmap


def _contour_sort_key(key: str) -> t.Tuple[int, str]:
    layer_id = parse_contour_id(key)
    if layer_id is not None:
        return (layer_id, key)
    if key in _TOPCON_LAYER_IDS:
        return (_TOPCON_LAYER_IDS[key], key)
    return (10**9, key)
