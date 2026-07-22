"""Heidelberg B-scan registration (E2E chunk 0x271C).

Applies the per-B-scan affine shape-adjust stored in the E2E: shear (Y),
scale (X), and translation about the B-scan centre. Used on B-scan pixels
(inverse map) and layer contours (forward map) so they stay aligned in
Heyex display space.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class BScanRegistration:
    """Parameters from Heidelberg B-scan registration chunk (0x271C)."""

    scale_x: float
    dx: float
    dy: float
    shear_y_angle: float

    def is_identity(self, atol: float = 1e-6) -> bool:
        return (
            abs(self.scale_x - 1.0) <= atol
            and abs(self.dx) <= atol
            and abs(self.dy) <= atol
            and abs(self.shear_y_angle) <= atol
        )


def registration_from_values(
    scale_x: float,
    dx: float,
    dy: float,
    shear_y_angle: float,
    values_1: list[float] | None = None,
) -> BScanRegistration:
    """Build registration; warn if constant slots differ from the known layout."""
    if values_1 is not None and len(values_1) >= 12:
        # Known constant pattern for unused slots in values_1
        expected = [None, 0.0, None, 0.0, 0.0, 0.0, None, 1.0, None, 0.0, 0.0, 0.0]
        for index, (exp, act) in enumerate(zip(expected, values_1)):
            if exp is not None and abs(float(act) - exp) > 1e-3:
                warnings.warn(
                    f"Unexpected BScanRegistration value at index {index}: "
                    f"expected {exp}, got {act}",
                    UserWarning,
                    stacklevel=2,
                )
                break
    return BScanRegistration(
        scale_x=float(scale_x),
        dx=float(dx),
        dy=float(dy),
        shear_y_angle=float(shear_y_angle),
    )


def build_inverse_registration_matrix(
    width: int,
    height: int,
    registration: BScanRegistration,
) -> np.ndarray:
    """3×3 inverse affine (homogeneous) for Heidelberg registration.

    Parameters in the E2E segment describe an inverse transform relative to
    the image centre — convenient for warping the B-scan.
    """
    shear_factor_y = math.tan(registration.shear_y_angle)
    dx = registration.dx
    dy = registration.dy
    scale_x = registration.scale_x

    change_origin = np.array(
        [
            [1.0, 0.0, -width / 2.0],
            [0.0, 1.0, -height / 2.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    revert_origin = np.array(
        [
            [1.0, 0.0, width / 2.0],
            [0.0, 1.0, height / 2.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    shear = np.array(
        [
            [1.0, 0.0, 0.0],
            [shear_factor_y, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    scale = np.array(
        [
            [scale_x, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    translate = np.array(
        [
            [1.0, 0.0, dx],
            [0.0, 1.0, dy],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )

    transform = np.eye(3, dtype=np.float64)
    # Applied right-to-left: change_origin → shear → scale → translate → revert
    for mat in (change_origin, shear, scale, translate, revert_origin):
        transform = mat @ transform
    return transform


def apply_registration_to_image(
    image: np.ndarray,
    inv_reg_matrix: np.ndarray,
) -> np.ndarray:
    """Warp B-scan with the inverse registration matrix (Heyex display space)."""
    height, width = image.shape[:2]
    m = inv_reg_matrix[:2, :].astype(np.float64)
    # OpenCV: dst(x,y) sampled from src(M @ [x,y,1]) — inverse map
    warped = cv2.warpAffine(
        image,
        m,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return warped.astype(image.dtype, copy=False)


def apply_registration_to_contour(
    contour_line: np.ndarray,
    reg_matrix: np.ndarray,
) -> np.ndarray:
    """Transform a 1-D layer height array with the forward registration matrix.

    Contour samples are (x=index, y=height). After the affine, x may land on a
    different column; out-of-bounds samples are dropped (NaN).
    """
    contour_line = np.asarray(contour_line, dtype=np.float64)
    width = len(contour_line)
    ret = np.full(width, np.nan, dtype=np.float64)

    xs = np.arange(width, dtype=np.float64)
    ys = contour_line
    valid_in = np.isfinite(ys)
    if not np.any(valid_in):
        return ret.astype(np.float32)

    ones = np.ones(np.count_nonzero(valid_in), dtype=np.float64)
    coords = np.stack([xs[valid_in], ys[valid_in], ones], axis=0)  # 3×N
    transformed = reg_matrix @ coords
    x_out = transformed[0]
    y_out = transformed[1]
    x_idx = np.floor(x_out).astype(np.int64)
    in_bounds = (x_idx >= 0) & (x_idx < width)
    for xi, yi in zip(x_idx[in_bounds], y_out[in_bounds]):
        ret[xi] = yi
    return ret.astype(np.float32)


def apply_registration_to_volume_slice(
    image: np.ndarray,
    registration: BScanRegistration | None,
) -> np.ndarray:
    """Register one B-scan image; no-op if registration is missing/identity."""
    if registration is None or registration.is_identity():
        return image
    height, width = image.shape[:2]
    inv = build_inverse_registration_matrix(width, height, registration)
    return apply_registration_to_image(image, inv)


def apply_registration_to_contour_slice(
    contour_line: np.ndarray,
    registration: BScanRegistration | None,
    width: int,
    height: int,
) -> np.ndarray:
    """Register one contour line; no-op if registration is missing/identity."""
    if registration is None or registration.is_identity():
        return contour_line
    if contour_line is None:
        return contour_line
    inv = build_inverse_registration_matrix(width, height, registration)
    forward = np.linalg.inv(inv)
    return apply_registration_to_contour(contour_line, forward)
