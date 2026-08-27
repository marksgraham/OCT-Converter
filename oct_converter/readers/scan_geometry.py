"""Scan geometry helpers for Heidelberg E2E circular / linear B-scans."""

from __future__ import annotations

import math
import typing as t
from dataclasses import dataclass

# Heidelberg BScanType values (chunk 10004 scanType)
BSCAN_TYPE_LINE = 1
BSCAN_TYPE_CIRCLE = 2


@dataclass
class ScanGeometry:
    """Geometry of an OPT scan relative to a fundus / localizer image."""

    scan_type: str  # "circular" | "linear" | "volume"
    start_angle: float | None = None  # radians from +x, [0, 2pi)
    centre: tuple[float, float] | None = None  # (x, y) fundus pixels
    radius: float | None = None
    line_start: tuple[float, float] | None = None
    line_end: tuple[float, float] | None = None

    @property
    def is_circular(self) -> bool:
        return self.scan_type == "circular"

    def to_dict(self) -> dict:
        return {
            "type": self.scan_type,
            "start_angle": self.start_angle,
            "centre": self.centre,
            "radius": self.radius,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }


def angle_from_origin(
    point: tuple[float, float], origin: tuple[float, float]
) -> float:
    """Angle of vector origin→point from +x axis, in [0, 2π)."""
    angle = math.atan2(point[1] - origin[1], point[0] - origin[0])
    if angle < 0:
        angle += 2 * math.pi
    return angle


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def fov_to_pixels(
    point: tuple[float, float],
    scan_angle: float,
    size_x: float,
    size_y: float,
) -> tuple[float, float]:
    """Convert FOV-degree position to fundus pixel coordinates.

    Uses fraction = 0.5 + position / scan_angle, then scales by IR image size.
    """
    if scan_angle == 0:
        return point
    fraction_x = 0.5 + point[0] / scan_angle
    fraction_y = 0.5 + point[1] / scan_angle
    return (size_x * fraction_x, size_y * fraction_y)


# Heidelberg interior-eye approximate conversion: 15° ≈ 4.4 mm
INTERIOR_DEGREES_TO_MM = 4.4 / 15.0


def heidelberg_resolutions_mm(
    line_start_fov: tuple[float, float],
    line_end_fov: tuple[float, float],
    num_columns: int,
    scaley: float,
    first_start_fov: tuple[float, float] | None = None,
    last_start_fov: tuple[float, float] | None = None,
    num_slices: int = 1,
) -> tuple[float, float, float]:
    """Return (res_width_mm, res_height_mm, res_depth_mm) for linear/volume scans.

    Width/depth come from FOV degree spans × INTERIOR_DEGREES_TO_MM;
    height is the B-scan axial scale (scaley).
    """
    scan_angle = distance(line_start_fov, line_end_fov)
    width_mm = scan_angle * INTERIOR_DEGREES_TO_MM
    res_width = width_mm / num_columns if num_columns else width_mm
    res_height = float(scaley)
    res_depth = 0.0
    if (
        num_slices > 1
        and first_start_fov is not None
        and last_start_fov is not None
    ):
        angle_z = distance(first_start_fov, last_start_fov)
        res_depth = (angle_z / (num_slices - 1)) * INTERIOR_DEGREES_TO_MM
    return res_width, res_height, res_depth


def circular_resolutions_mm(
    line_start_fov: tuple[float, float],
    centre_fov: tuple[float, float],
    num_columns: int,
    scaley: float,
) -> tuple[float, float, float]:
    """Return (res_width_mm, res_height_mm, res_depth_mm) for circular scans.

    Lateral spacing uses circle perimeter (diameter × π) in interior-eye mm.
    """
    diameter = distance(line_start_fov, centre_fov) * 2
    width_mm = diameter * math.pi * INTERIOR_DEGREES_TO_MM
    res_width = width_mm / num_columns if num_columns else width_mm
    return res_width, float(scaley), 0.0


def fundus_localizer_params(
    fundus_info: t.Any | None,
) -> tuple[tuple[float, float] | None, float | None]:
    """Extract (fundus_size_xy, scan_angle_deg) from E2E chunk-type-5 info.

    Returns (None, None) when size or angle look invalid.
    """
    if fundus_info is None:
        return None, None
    try:
        fx = float(fundus_info.ir_image_size_x)
        fy = float(fundus_info.ir_image_size_y)
        sa = float(fundus_info.scan_angle)
    except (AttributeError, TypeError, ValueError):
        return None, None
    if fx > 0 and fy > 0 and 0 < sa < 180:
        return (fx, fy), sa
    return None, None


def geometry_from_bscan_metadata(
    scan_type_raw: int,
    pos_x1: float,
    pos_y1: float,
    pos_x2: float,
    pos_y2: float,
    centre_x: float,
    centre_y: float,
    fundus_size: tuple[float, float] | None = None,
    scan_angle: float | None = None,
    num_slices: int = 1,
) -> ScanGeometry:
    """Build ScanGeometry from E2E bscan_metadata fields (FOV degrees).

    ``line_start`` / ``line_end`` / ``centre`` / ``radius`` are fundus-pixel
    coordinates only when ``fundus_size`` and ``scan_angle`` allow FOV→pixel
    conversion. Otherwise those fields are left ``None`` so callers do not
    treat FOV degrees as pixel indices (e.g. DICOM ReferenceCoordinates).
    Circular ``start_angle`` is still derived from FOV positions (scale-invariant).
    """
    line_start_fov = (float(pos_x1), float(pos_y1))
    line_end_fov = (float(pos_x2), float(pos_y2))
    centre_fov = (float(centre_x), float(centre_y))

    can_convert = (
        fundus_size is not None
        and scan_angle is not None
        and scan_angle > 0
        and fundus_size[0] > 0
        and fundus_size[1] > 0
    )
    if can_convert:
        size_x, size_y = fundus_size
        line_start = fov_to_pixels(line_start_fov, scan_angle, size_x, size_y)
        line_end = fov_to_pixels(line_end_fov, scan_angle, size_x, size_y)
        centre = fov_to_pixels(centre_fov, scan_angle, size_x, size_y)
        radius = distance(line_start, centre)
    else:
        line_start = None
        line_end = None
        centre = None
        radius = None

    if scan_type_raw == BSCAN_TYPE_CIRCLE:
        return ScanGeometry(
            scan_type="circular",
            # Angle from FOV vectors is valid even without pixel conversion.
            start_angle=angle_from_origin(line_start_fov, centre_fov),
            centre=centre,
            radius=radius,
            line_start=line_start,
            line_end=line_end,
        )
    if num_slices > 1:
        return ScanGeometry(
            scan_type="volume",
            line_start=line_start,
            line_end=line_end,
        )
    return ScanGeometry(
        scan_type="linear",
        line_start=line_start,
        line_end=line_end,
    )


def build_volume_scan_geometry(
    bscan_by_slice: dict[int, t.Any],
    num_slices: int,
    num_columns: int,
    default_pixel_spacing: list[float] | None,
    slice_thickness: float,
    fundus_info: t.Any | None = None,
) -> tuple[dict | None, list[float] | None]:
    """Derive scan_geometry dict and pixel_spacing for one E2E OCT volume.

    Args:
        bscan_by_slice: Map of slice index → bscan_metadata (chunk 10004).
        num_slices: Number of B-scans in the volume list.
        num_columns: A-scan count (B-scan width).
        default_pixel_spacing: Fallback ``[scalex, scaley, slice_thickness]``.
        slice_thickness: Default Z spacing when depth cannot be derived.
        fundus_info: Optional chunk-type-5 fundus / IR localizer info.

    Returns:
        (scan_geometry_dict or None, pixel_spacing [x, y, z] or default).
    """
    if not bscan_by_slice:
        return None, default_pixel_spacing

    fundus_size, scan_angle = fundus_localizer_params(fundus_info)
    first_idx = min(bscan_by_slice.keys())
    last_idx = max(bscan_by_slice.keys())
    first_md = bscan_by_slice[first_idx]
    last_md = bscan_by_slice[last_idx]

    geom = geometry_from_bscan_metadata(
        scan_type_raw=int(first_md.scanType),
        pos_x1=float(first_md.posX1),
        pos_y1=float(first_md.posY1),
        pos_x2=float(first_md.posX2),
        pos_y2=float(first_md.posY2),
        centre_x=float(first_md.centrePosX),
        centre_y=float(first_md.centrePosY),
        fundus_size=fundus_size,
        scan_angle=scan_angle,
        num_slices=num_slices,
    )
    scan_geometry = geom.to_dict()

    # Per-frame line endpoints for volume / raster OPT DICOM (fundus pixels only)
    if (
        geom.scan_type != "circular"
        and len(bscan_by_slice) > 1
        and geom.line_start is not None
    ):
        frame_lines: list[dict | None] = []
        for slice_idx in range(num_slices):
            md = bscan_by_slice.get(slice_idx)
            if md is None:
                frame_lines.append(None)
                continue
            g = geometry_from_bscan_metadata(
                scan_type_raw=int(md.scanType),
                pos_x1=float(md.posX1),
                pos_y1=float(md.posY1),
                pos_x2=float(md.posX2),
                pos_y2=float(md.posY2),
                centre_x=float(md.centrePosX),
                centre_y=float(md.centrePosY),
                fundus_size=fundus_size,
                scan_angle=scan_angle,
                num_slices=1,
            )
            frame_lines.append(
                {
                    "line_start": list(g.line_start) if g.line_start else None,
                    "line_end": list(g.line_end) if g.line_end else None,
                }
            )
        scan_geometry["frame_lines"] = frame_lines

    try:
        if geom.scan_type == "circular":
            res_w, res_h, res_d = circular_resolutions_mm(
                (float(first_md.posX1), float(first_md.posY1)),
                (float(first_md.centrePosX), float(first_md.centrePosY)),
                num_columns,
                float(first_md.scaley),
            )
        else:
            res_w, res_h, res_d = heidelberg_resolutions_mm(
                (float(first_md.posX1), float(first_md.posY1)),
                (float(first_md.posX2), float(first_md.posY2)),
                num_columns,
                float(first_md.scaley),
                first_start_fov=(
                    float(first_md.posX1),
                    float(first_md.posY1),
                ),
                last_start_fov=(
                    float(last_md.posX1),
                    float(last_md.posY1),
                ),
                num_slices=num_slices,
            )
        # OCTVolumeWithMetaData / e2e_image_geom expect [scalex, scaley, z]
        pixel_spacing = [res_w, res_h, res_d if res_d else slice_thickness]
    except Exception:
        pixel_spacing = default_pixel_spacing

    return scan_geometry, pixel_spacing


def circle_reference_coordinates(
    centre: tuple[float, float],
    radius: float,
    start_angle: float,
    num_columns: int,
) -> list[float]:
    """Build DICOM ReferenceCoordinates for a circular B-scan.

    Returns 2N floats as (row, col) pairs — DICOM order — for each OPT column.
    Column 0 is at ``start_angle`` from +x; angle increases counterclockwise.
    """
    cx, cy = centre
    coords: list[float] = []
    if num_columns <= 0:
        return coords
    for i in range(num_columns):
        theta = start_angle + (2 * math.pi * i / num_columns)
        x = cx + radius * math.cos(theta)
        y = cy + radius * math.sin(theta)
        # DICOM: first of pair = row (vertical), second = column (horizontal)
        coords.append(float(y))
        coords.append(float(x))
    return coords


def start_angle_from_reference_coordinates(
    reference_coordinates: t.Sequence[float],
) -> float | None:
    """Recover start_angle (radians) from NONLINEAR ReferenceCoordinates.

    Fits a circle centre as the mean of the polyline points, then takes
    atan2 of the vector from centre to the first sample.
    """
    if len(reference_coordinates) < 4:
        return None
    xs = []
    ys = []
    for i in range(0, len(reference_coordinates) - 1, 2):
        row = float(reference_coordinates[i])
        col = float(reference_coordinates[i + 1])
        ys.append(row)
        xs.append(col)
    if not xs:
        return None
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    angle = angle_from_origin((xs[0], ys[0]), (cx, cy))
    # Treat 2π as 0 for numerical stability
    if abs(angle - 2 * math.pi) < 1e-6:
        return 0.0
    return angle


# CID 4272 OPT Scan Pattern Type
SCAN_PATTERN_CUBE = ("DCM", "128279", "Cube B-scan pattern")
SCAN_PATTERN_RASTER = ("DCM", "128280", "Raster B-scan pattern")
SCAN_PATTERN_LINE = ("DCM", "128281", "Line B-scan pattern")
SCAN_PATTERN_CIRCLE = ("DCM", "128284", "Circle B-scan pattern")


def scan_pattern_code(geometry: ScanGeometry | None, num_frames: int) -> tuple[str, str, str]:
    """Return (scheme, value, meaning) for ScanPatternTypeCodeSequence."""
    if geometry is not None and geometry.is_circular:
        return SCAN_PATTERN_CIRCLE
    if geometry is not None and geometry.scan_type == "linear":
        return SCAN_PATTERN_LINE
    if num_frames > 1:
        return SCAN_PATTERN_CUBE
    return SCAN_PATTERN_LINE
