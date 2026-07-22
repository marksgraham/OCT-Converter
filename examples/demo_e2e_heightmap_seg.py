"""Demonstrate E2E layer segmentation export as Height Map Segmentation DICOM.

When an E2E volume includes Heidelberg layer contours, create_dicom_from_oct()
also writes a Height Map Segmentation Storage file (SOP Class UID
1.2.840.10008.5.1.4.1.1.66.8) alongside the OPT volume and fundus images:

    {stem}_oct_{n}.dcm   - Ophthalmic Tomography (OPT) volume
    {stem}_fundus_{n}.dcm - fundus / enface image (if present)
    {stem}_seg_{n}.dcm   - Height Map Segmentation (layer surfaces)

Each SEG frame is one retinal layer. Rows are B-scans; columns are A-scans.
Pixel values are axial heights in fractional B-scan pixels from the top of
the frame (NaN / missing samples use Float Pixel Padding Value = -1).

The SEG instance shares StudyInstanceUID and FrameOfReferenceUID with its
companion OPT file and references that OPT via the Derivation Image functional
group.
"""

from pathlib import Path

import numpy as np
import pydicom

from oct_converter.dicom import create_dicom_from_oct
from oct_converter.dicom.heightmap import (
    HEIGHTMAP_PADDING_VALUE,
    HEIDELBERG_LAYER_NAMES,
)
from oct_converter.readers import E2E

filepath = "../sample_files/sample.E2E"
output_dir = Path("e2e_dicom_out")

# Inspect contours already attached to each OCT volume (chunk type 10019).
e2e = E2E(filepath)
for volume in e2e.read_oct_volume():
    if not volume.contours:
        print(f"{volume.volume_id}: no layer contours")
        continue
    print(f"{volume.volume_id} laterality={volume.laterality}")
    for key, slices in volume.contours.items():
        layer_id = int(key.replace("contour", ""))
        name = HEIDELBERG_LAYER_NAMES.get(layer_id, key)
        n_valid = sum(
            1 for s in slices if s is not None and np.isfinite(s).any()
        )
        print(f"  {key} ({name}): {n_valid}/{len(slices)} B-scans with data")
    # Overlay contours on a montage of B-scans
    volume.peek(show_contours=True)

# Convert: writes OPT (+ fundus) and, when contours exist, Height Map SEG.
written = create_dicom_from_oct(filepath, output_dir=str(output_dir))
for path in written:
    print(f"wrote {path}")

# Inspect a Height Map Segmentation DICOM.
for path in written:
    if "_seg_" not in Path(path).name:
        continue
    seg = pydicom.dcmread(str(path))
    print("\nHeight Map Segmentation")
    print(f"  SOP Class:  {seg.SOPClassUID}")
    print(f"  Modality:   {seg.Modality}")
    print(f"  Type:       {seg.SegmentationType}")
    print(f"  Frames:     {seg.NumberOfFrames} (one per layer)")
    print(f"  Rows x Cols:{seg.Rows} x {seg.Columns}  (B-scans x A-scans)")
    print(f"  FOR UID:    {seg.FrameOfReferenceUID}")

    for item in seg.SegmentSequence:
        print(
            f"  Segment {item.SegmentNumber}: {item.SegmentLabel} "
            f"({item.SegmentedPropertyTypeCodeSequence[0].CodeMeaning})"
        )

    heights = np.frombuffer(seg.FloatPixelData, dtype="<f4").reshape(
        int(seg.NumberOfFrames), int(seg.Rows), int(seg.Columns)
    )
    valid = heights != HEIGHTMAP_PADDING_VALUE
    print(
        f"  Height range (valid samples): "
        f"[{heights[valid].min():.2f}, {heights[valid].max():.2f}] px"
        if valid.any()
        else "  No valid height samples"
    )

    # Companion OPT is referenced for spatial context.
    source = (
        seg.SharedFunctionalGroupsSequence[0]
        .DerivationImageSequence[0]
        .SourceImageSequence[0]
    )
    print(f"  Derived from OPT SOP Instance: {source.ReferencedSOPInstanceUID}")
