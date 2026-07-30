"""Demonstrate FDA layer segmentation export as Height Map Segmentation DICOM.

When an FDA volume includes Topcon layer contours, create_dicom_from_oct()
also writes a Height Map Segmentation Storage file (SOP Class UID
1.2.840.10008.5.1.4.1.1.66.8) alongside the OPT volume and fundus images:

    {stem}.dcm                 - Ophthalmic Tomography (OPT) volume
    {stem}_fundus.dcm          - color fundus (if present)
    {stem}_fundus_grayscale.dcm - grayscale fundus (if present)
    {stem}_seg.dcm             - Height Map Segmentation (layer surfaces)

How height values are stored (DICOM PS3.3 A.91 / C.8.20.5)
----------------------------------------------------------
* SegmentationType = HEIGHTMAP; heights live in Float Pixel Data (7FE0,0008),
  not Pixel Data (7FE0,0010).
* Array shape after reshape: (n_layers, n_bscans, n_ascans)
  - frame i  <-> one retinal surface (see SegmentSequence[i])
  - row      <-> OPT B-scan frame index
  - column   <-> A-scan column (same as OPT Columns)
* Each float is axial height in fractional B-scan pixels from the *top*
  of that B-scan (row 0 of the OPT frame). Valid range is [0, OPT.Rows].
* Missing samples use Float Pixel Padding Value (-1.0 here).
* Millimetres: height_mm = height_px * RealWorldValueSlope (RWVM functional
  group; intercept 0). Padding values must not be mapped.
* Layer names/codes: SegmentSequence (SegmentLabel, CID 4273 property type).
* Companion OPT: same StudyInstanceUID and FrameOfReferenceUID; OPT SOP is
  referenced via Derivation Image / Referenced Series.

Minimal read example::

    import numpy as np
    import pydicom

    seg = pydicom.dcmread("sample_seg.dcm")
    heights = np.frombuffer(seg.FloatPixelData, dtype="<f4").reshape(
        int(seg.NumberOfFrames), int(seg.Rows), int(seg.Columns)
    )
    pad = float(seg.FloatPixelPaddingValue)  # -1.0
    labels = [s.SegmentLabel for s in seg.SegmentSequence]
    slope = float(
        seg.SharedFunctionalGroupsSequence[0]
        .RealWorldValueMappingSequence[0]
        .RealWorldValueSlope
    )
    heights_mm = np.where(heights == pad, np.nan, heights * slope)

See also: examples/demo_e2e_heightmap_seg.py for the E2E path.
"""

from pathlib import Path

import numpy as np
import pydicom

from oct_converter.dicom import create_dicom_from_oct
from oct_converter.dicom.heightmap import (
    HEIGHTMAP_PADDING_VALUE,
    TOPCON_LAYER_LABELS,
)
from oct_converter.readers import FDA


def read_heightmap_seg(path: str | Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load a Height Map SEG DICOM written by oct_converter.

    Returns:
        heights_px: float32 array (n_layers, n_bscans, n_ascans), pixels from
            top of B-scan; padding samples are left as FloatPixelPaddingValue.
        heights_mm: same shape; padding set to NaN; px * RWVM slope.
        labels: SegmentLabel per layer (frame order).
    """
    seg = pydicom.dcmread(str(path))
    heights_px = np.frombuffer(seg.FloatPixelData, dtype="<f4").reshape(
        int(seg.NumberOfFrames), int(seg.Rows), int(seg.Columns)
    )
    pad = float(getattr(seg, "FloatPixelPaddingValue", HEIGHTMAP_PADDING_VALUE))
    labels = [str(item.SegmentLabel) for item in seg.SegmentSequence]

    rwvm = seg.SharedFunctionalGroupsSequence[0].RealWorldValueMappingSequence[0]
    slope = float(rwvm.RealWorldValueSlope)
    heights_mm = heights_px.astype(np.float64) * slope
    heights_mm[heights_px == pad] = np.nan
    return heights_px, heights_mm, labels


filepath = "../path/to/sample.fda"
output_dir = Path("../path/to/fda_dicom_out")

# Inspect contours already attached to the OCT volume (@CONTOUR_INFO).
fda = FDA(filepath)
volume = fda.read_oct_volume()
if not volume.contours:
    print("no layer contours")
else:
    print(f"laterality={volume.laterality}")
    for key, arr in volume.contours.items():
        data = np.asarray(arr)
        label = TOPCON_LAYER_LABELS.get(key, key)
        n_valid = int(np.isfinite(data).sum()) if data.size else 0
        print(
            f"  {key} (-> {label}): shape={data.shape}, "
            f"{n_valid}/{data.size} finite samples"
        )
    volume.peek(show_contours=True)

# Convert: writes OPT (+ fundus) and, when contours exist, Height Map SEG.
written = create_dicom_from_oct(filepath, output_dir=str(output_dir))
for path in written:
    print(f"wrote {path}")

# Read and inspect Height Map Segmentation DICOMs.
for path in written:
    if not Path(path).stem.endswith("_seg"):
        continue
    seg = pydicom.dcmread(str(path))
    heights_px, heights_mm, labels = read_heightmap_seg(path)

    print("\nHeight Map Segmentation")
    print(f"  SOP Class:  {seg.SOPClassUID}")
    print(f"  Modality:   {seg.Modality}")
    print(f"  Type:       {seg.SegmentationType}")
    print(f"  shape:      {heights_px.shape}  (layers, B-scans, A-scans)")
    print(f"  FOR UID:    {seg.FrameOfReferenceUID}")

    for item in seg.SegmentSequence:
        print(
            f"  Segment {item.SegmentNumber}: {item.SegmentLabel} "
            f"({item.SegmentedPropertyTypeCodeSequence[0].CodeMeaning})"
        )

    valid = np.isfinite(heights_mm)
    print(
        f"  Height range (valid): "
        f"[{heights_px[valid].min():.2f}, {heights_px[valid].max():.2f}] px / "
        f"[{heights_mm[valid].min():.4f}, {heights_mm[valid].max():.4f}] mm"
        if valid.any()
        else "  No valid height samples"
    )

    # Example: ILM surface on B-scan 0 (if present).
    if "ILM" in labels:
        ilm = heights_px[labels.index("ILM")]
        masked = np.where(ilm == HEIGHTMAP_PADDING_VALUE, np.nan, ilm)
        print(f"  ILM B-scan 0 (px): min={np.nanmin(masked[0]):.2f}")

    source = (
        seg.SharedFunctionalGroupsSequence[0]
        .DerivationImageSequence[0]
        .SourceImageSequence[0]
    )
    print(f"  Derived from OPT SOP Instance: {source.ReferencedSOPInstanceUID}")
