from __future__ import annotations

import typing as t
from datetime import datetime
from importlib import metadata
from pathlib import Path

import numpy as np
from construct import StreamError, StringError
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import (
    ExplicitVRLittleEndian,
    OphthalmicPhotography16BitImageStorage,
    OphthalmicTomographyImageStorage,
    UID,
    generate_uid,
)
from pydicom.valuerep import DSfloat

from oct_converter.dicom.boct_meta import boct_dicom_metadata
from oct_converter.dicom.e2e_meta import e2e_dicom_metadata
from oct_converter.dicom.fda_meta import fda_dicom_metadata
from oct_converter.dicom.fds_meta import fds_dicom_metadata
from oct_converter.dicom.heightmap import (
    HEIGHTMAP_PADDING_VALUE,
    contours_to_heightmaps,
)
from oct_converter.dicom.img_meta import img_dicom_metadata
from oct_converter.dicom.metadata import DicomMetadata
from oct_converter.dicom.poct_meta import poct_dicom_metadata
from oct_converter.exceptions import InvalidOCTReaderError
from oct_converter.readers import BOCT, E2E, FDA, FDS, IMG, POCT
from oct_converter.readers.scan_geometry import (
    ScanGeometry,
    circle_reference_coordinates,
    scan_pattern_code,
)

# Deterministic implementation UID based on package name and version
version = metadata.version("oct_converter")
implementation_uid = generate_uid(entropy_srcs=["oct_converter", version])

# PS3.4 Height Map Segmentation Storage (not yet in all pydicom releases)
HeightMapSegmentationStorage = UID("1.2.840.10008.5.1.4.1.1.66.8")

# Acquisition timestamps from readers are either datetime or this string form.
_ACQUISITION_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _coerce_datetime(value: datetime | str | None) -> datetime | None:
    """Normalize reader acquisition timestamps to ``datetime`` or ``None``."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.strptime(value, _ACQUISITION_DATETIME_FORMAT)
    raise TypeError(f"Expected datetime or str, got {type(value)!r}")


def set_content_date_time(ds: Dataset, when: datetime | None = None) -> None:
    """Set ContentDate / ContentTime (when this DICOM instance was created)."""
    when = when or datetime.now()
    ds.ContentDate = when.strftime("%Y%m%d")
    ds.ContentTime = when.strftime("%H%M%S.%f")


def format_dicom_date(value: datetime | str | None) -> str:
    """Format a timestamp as DICOM DA (YYYYMMDD), or ``\"\"`` if missing."""
    dt = _coerce_datetime(value)
    return dt.strftime("%Y%m%d") if dt else ""


def format_dicom_time(value: datetime | str | None) -> str:
    """Format a timestamp as DICOM TM (HHMMSS.ffffff), or ``\"\"`` if missing."""
    dt = _coerce_datetime(value)
    return dt.strftime("%H%M%S.%f") if dt else ""


def format_acquisition_datetime(value: datetime | str | None) -> str:
    """Format a timestamp as DICOM DT, or ``\"\"`` if missing."""
    dt = _coerce_datetime(value)
    return dt.strftime("%Y%m%d%H%M%S.%f") if dt else ""


def opt_base_dicom(filepath: Path) -> Dataset:
    """Creates the base dicom to be populated.

    Args:
            filepath: Path to where output file is to be saved
    Returns:
            ds: FileDataset with file meta, preamble, and empty dataset
    """
    # Populate required values for file meta information
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = OphthalmicTomographyImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = implementation_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    # Create the FileDataset instance with file meta, preamble and empty DS
    ds = FileDataset(str(filepath), {}, file_meta=file_meta, preamble=b"\0" * 128)
    return ds


def populate_patient_info(ds: Dataset, meta: DicomMetadata) -> Dataset:
    """Populates Patient Module PS3.3 C.7.1.1

    Args:
            ds: current dataset
            meta: DICOM metadata information
    Returns:
            ds: Dataset, updated with patient information
    """
    # Patient Module PS3.3 C.7.1.1
    ds.PatientName = f"{meta.patient_info.last_name or ''}^{meta.patient_info.first_name or ''}"
    ds.PatientID = meta.patient_info.patient_id or ""
    ds.PatientSex = meta.patient_info.patient_sex or ""
    ds.PatientBirthDate = (
        meta.patient_info.patient_dob.strftime("%Y%m%d")
        if meta.patient_info.patient_dob
        else ""
    )
    return ds


def populate_manufacturer_info(ds: Dataset, meta: DicomMetadata) -> Dataset:
    """Populates equipment modules PS3.3 C.7.5.1, PS3.3 C.7.5.2

    Args:
            ds: current dataset
            meta: DICOM metadata information
    Returns:
            ds: Dataset, updated with equipment information
    """
    # General and enhanced equipment module PS3.3 C.7.5.1, PS3.3 C.7.5.2
    ds.Manufacturer = meta.manufacturer_info.manufacturer
    ds.ManufacturerModelName = meta.manufacturer_info.manufacturer_model
    ds.DeviceSerialNumber = meta.manufacturer_info.device_serial
    ds.SoftwareVersions = meta.manufacturer_info.software_version

    # OPT parameter module PS3.3 C.8.17.9
    cd, cv, cm = meta.oct_image_params.opt_acquisition_device.value
    ds.AcquisitionDeviceTypeCodeSequence = [Dataset()]
    ds.AcquisitionDeviceTypeCodeSequence[0].CodeValue = cv
    ds.AcquisitionDeviceTypeCodeSequence[0].CodingSchemeDesignator = cd
    ds.AcquisitionDeviceTypeCodeSequence[0].CodeMeaning = cm
    ds.DetectorType = meta.oct_image_params.DetectorType.value
    return ds


def populate_opt_series(
    ds: Dataset,
    meta: DicomMetadata,
    study_instance_uid: str | None = None,
    series_instance_uid: str | None = None,
    sop_instance_uid: str | None = None,
) -> Dataset:
    """Populates study and series modules, PS3.3 C.7.2.1, PS3.3 C.7.3.1,
    PS3.3 C.8.17.6, and PS3.3 C.12.1

    Args:
            ds: current dataset
            meta: DICOM metadata information
            study_instance_uid: Optional shared Study Instance UID
            series_instance_uid: Optional Series Instance UID
            sop_instance_uid: Optional SOP Instance UID
    Returns:
            ds: Dataset, updated with study and series information
    """
    # General study / series UIDs (optional overrides keep OPT/SEG/fundus linked)
    ds.StudyInstanceUID = study_instance_uid or generate_uid()
    ds.SeriesInstanceUID = series_instance_uid or generate_uid()
    ds.StudyID = meta.series_info.study_id
    ds.StudyDate = format_dicom_date(meta.series_info.acquisition_date)
    ds.StudyTime = format_dicom_time(meta.series_info.acquisition_date)
    ds.Laterality = meta.series_info.laterality
    ds.ProtocolName = meta.series_info.protocol
    ds.SeriesDescription = meta.series_info.description
    # Ophthalmic Tomography Series PS3.3 C.8.17.6
    ds.Modality = "OPT"
    try:
        ds.SeriesNumber = int(meta.series_info.series_id)
    except (TypeError, ValueError):
        ds.SeriesNumber = 1

    # SOP Common module PS3.3 C.12.1
    ds.SOPClassUID = OphthalmicTomographyImageStorage
    ds.SOPInstanceUID = sop_instance_uid or generate_uid()
    return ds


def populate_ocular_region(ds: Dataset, meta: DicomMetadata) -> Dataset:
    """Populates ocular region modules, PS3.3 C.8.17.5, PS3.3 C.7.6.16.2.8,
    and PS3.3 C.7.6.16.2.1

    Args:
            ds: current dataset
            meta: DICOM metadata information
    Returns:
            ds: Dataset, updated with ocular region information
    """
    # Ocular region imaged module PS3.3 C.8.17.5
    cd, cv, cm = meta.series_info.opt_anatomy.value
    ds.ImageLaterality = meta.series_info.laterality
    ds.AnatomicRegionSequence = [Dataset()]
    ds.AnatomicRegionSequence[0].CodeValue = cv
    ds.AnatomicRegionSequence[0].CodingSchemeDesignator = cd
    ds.AnatomicRegionSequence[0].CodeMeaning = cm
    return ds


def opt_shared_functional_groups(ds: Dataset, meta: DicomMetadata) -> Dataset:
    # ---- Shared
    shared_ds = [Dataset()]
    # Frame anatomy PS3.3 C.7.6.16.2.8
    shared_ds[0].FrameAnatomySequence = [Dataset()]
    shared_ds[0].FrameAnatomySequence[0].FrameLaterality = meta.series_info.laterality
    shared_ds[0].FrameAnatomySequence[0].AnatomicRegionSequence = [
        ds.AnatomicRegionSequence[0].copy()
    ]
    # Pixel Measures PS3.3 C.7.6.16.2.1
    shared_ds[0].PixelMeasuresSequence = [Dataset()]
    shared_ds[0].PixelMeasuresSequence[
        0
    ].PixelSpacing = meta.image_geometry.pixel_spacing
    shared_ds[0].PixelMeasuresSequence[
        0
    ].SliceThickness = meta.image_geometry.slice_thickness
    # Plane Orientation PS3.3 C.7.6.16.2.4
    shared_ds[0].PlaneOrientationSequence = [Dataset()]
    shared_ds[0].PlaneOrientationSequence[
        0
    ].ImageOrientationPatient = meta.image_geometry.image_orientation
    ds.SharedFunctionalGroupsSequence = shared_ds
    return ds


def write_opt_dicom(
    meta: DicomMetadata,
    frames: t.List[np.ndarray],
    filepath: Path,
    study_instance_uid: str | None = None,
    frame_of_reference_uid: str | None = None,
    series_instance_uid: str | None = None,
    sop_instance_uid: str | None = None,
    fundus_ds: Dataset | None = None,
) -> FileDataset:
    """Writes required DICOM metadata and oct pixel data to .dcm file.

    Args:
            meta: DICOM metadata information
            frames: list of frames of pixel data
            filepath: Path to where output file is being saved
            study_instance_uid: Optional shared Study Instance UID
            frame_of_reference_uid: Optional shared Frame of Reference UID
            series_instance_uid: Optional Series Instance UID
            sop_instance_uid: Optional SOP Instance UID
            fundus_ds: Optional companion fundus FileDataset for Ophthalmic
                Frame Location (circular / linear scan overlay on localizer)
    Returns:
            FileDataset of the written OPT instance (path is ``filepath``)
    """
    ds = opt_base_dicom(filepath)
    ds = populate_patient_info(ds, meta)
    ds = populate_manufacturer_info(ds, meta)
    ds = populate_opt_series(
        ds,
        meta,
        study_instance_uid=study_instance_uid,
        series_instance_uid=series_instance_uid,
        sop_instance_uid=sop_instance_uid,
    )
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds = populate_ocular_region(ds, meta)
    ds = opt_shared_functional_groups(ds, meta)

    # Frame of Reference Module PS3.3 C.7.4.1
    ds.FrameOfReferenceUID = frame_of_reference_uid or generate_uid()

    # OPT Image Module PS3.3 C.8.17.7
    ds.ImageType = ["DERIVED", "SECONDARY"]
    ds.SamplesPerPixel = 1
    ds.AcquisitionDateTime = format_acquisition_datetime(
        meta.series_info.acquisition_date
    )

    ds.AcquisitionNumber = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    # Unsigned integer
    ds.PixelRepresentation = 0
    # Use 16 bit pixel
    ds.BitsAllocated = 16
    ds.BitsStored = ds.BitsAllocated
    ds.HighBit = ds.BitsAllocated - 1
    ds.SamplesPerPixel = 1
    ds.NumberOfFrames = len(frames)

    # Multi-frame Functional Groups Module PS3.3 C.7.6.16
    set_content_date_time(ds)
    ds.InstanceNumber = 1

    # Scan Pattern Type (CID 4272) — Ophthalmic Tomography Parameters
    geom = meta.scan_geometry
    scheme, value, meaning = scan_pattern_code(
        ScanGeometry(
            scan_type=geom.scan_type if geom else "volume",
            start_angle=geom.start_angle if geom else None,
            centre=tuple(geom.centre) if geom and geom.centre else None,
            radius=geom.radius if geom else None,
        )
        if geom
        else None,
        len(frames),
    )
    ds.ScanPatternTypeCodeSequence = [_code_dataset(scheme, value, meaning)]

    per_frame = []
    # Normalize
    frames = normalize_volume(frames)
    # Convert to a 3d volume
    pixel_data = np.array(frames).astype(np.uint16)
    ds.Rows = pixel_data.shape[1]
    ds.Columns = pixel_data.shape[2]
    for i in range(pixel_data.shape[0]):
        # Per Frame Functional Groups
        frame_fgs = Dataset()
        frame_fgs.PlanePositionSequence = [Dataset()]
        ipp = [0, 0, DSfloat(i * meta.image_geometry.slice_thickness, auto_format=True)]
        frame_fgs.PlanePositionSequence[0].ImagePositionPatient = ipp
        frame_fgs.FrameContentSequence = [Dataset()]
        frame_fgs.FrameContentSequence[0].InStackPositionNumber = i + 1
        frame_fgs.FrameContentSequence[0].StackID = "1"

        # Ophthalmic Frame Location Macro (circular / linear vs fundus)
        if fundus_ds is not None and geom is not None:
            loc = Dataset()
            loc.ReferencedSOPClassUID = fundus_ds.SOPClassUID
            loc.ReferencedSOPInstanceUID = fundus_ds.SOPInstanceUID
            loc.PurposeOfReferenceCodeSequence = [
                _code_dataset("DCM", "121311", "Localizer")
            ]
            if geom.scan_type == "circular" and geom.centre and geom.radius is not None:
                loc.OphthalmicImageOrientation = "NONLINEAR"
                loc.ReferenceCoordinates = circle_reference_coordinates(
                    tuple(geom.centre),
                    float(geom.radius),
                    float(geom.start_angle or 0.0),
                    int(ds.Columns),
                )
                frame_fgs.OphthalmicFrameLocationSequence = [loc]
            else:
                line_start = geom.line_start
                line_end = geom.line_end
                if geom.frame_lines and i < len(geom.frame_lines):
                    fl = geom.frame_lines[i]
                    if fl and fl.get("line_start") and fl.get("line_end"):
                        line_start = fl["line_start"]
                        line_end = fl["line_end"]
                if line_start and line_end:
                    loc.OphthalmicImageOrientation = "LINEAR"
                    # DICOM (row, col) = (y, x)
                    sx, sy = line_start
                    ex, ey = line_end
                    loc.ReferenceCoordinates = [
                        float(sy),
                        float(sx),
                        float(ey),
                        float(ex),
                    ]
                    frame_fgs.OphthalmicFrameLocationSequence = [loc]

        per_frame.append(frame_fgs)
    ds.PerFrameFunctionalGroupsSequence = per_frame
    ds.PixelData = pixel_data.tobytes()
    ds.save_as(
        filepath, implicit_vr=False, little_endian=True, enforce_file_format=True
    )
    return ds


def _code_dataset(scheme: str, value: str, meaning: str) -> Dataset:
    """Build a DICOM coded-entry sequence item."""
    item = Dataset()
    item.CodeValue = value
    item.CodingSchemeDesignator = scheme
    item.CodeMeaning = meaning
    return item


def write_heightmap_seg_dicom(
    meta: DicomMetadata,
    contours: dict,
    opt_ds: Dataset,
    filepath: Path,
    axial_spacing_mm: float | None = None,
) -> Path | None:
    """Write a Height Map Segmentation DICOM from OCT layer contours.

    Accepts E2E (``contour{id}`` lists) or FDA (named 2-D arrays) contour
    dicts; see ``contours_to_heightmaps``.

    Args:
            meta: DICOM metadata (patient/equipment/geometry)
            contours: ``OCTVolumeWithMetaData.contours`` dict
            opt_ds: Companion OPT FileDataset (must include FOR and SOP UIDs)
            filepath: Output path for the SEG file
            axial_spacing_mm: Axial (B-scan row) spacing in mm for RWVM.
                Defaults to OPT pixel spacing row component when available.
    Returns:
            Path to written SEG file, or None if no contours to encode.
    """
    num_bscans = int(opt_ds.NumberOfFrames)
    width = int(opt_ds.Columns)
    opt_rows = int(opt_ds.Rows)
    layers = contours_to_heightmaps(contours, num_bscans, width)
    if not layers:
        return None

    # Prefer caller-supplied axial spacing; fall back to OPT row spacing.
    if axial_spacing_mm is None:
        if meta.image_geometry.pixel_spacing:
            axial_spacing_mm = float(meta.image_geometry.pixel_spacing[0])
        else:
            axial_spacing_mm = 1.0

    # Heightmap Pixel Measures: row = B-scan spacing, col = OPT column spacing
    opt_col_spacing = float(meta.image_geometry.pixel_spacing[1]) if meta.image_geometry.pixel_spacing else 1.0
    slice_thickness = float(meta.image_geometry.slice_thickness)
    image_orientation = list(meta.image_geometry.image_orientation) or [
        1,
        0,
        0,
        0,
        1,
        0,
    ]

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = HeightMapSegmentationStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = implementation_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(filepath), {}, file_meta=file_meta, preamble=b"\0" * 128)

    ds = populate_patient_info(ds, meta)
    # Equipment without OPT-only AcquisitionDeviceType (still useful)
    ds.Manufacturer = meta.manufacturer_info.manufacturer
    ds.ManufacturerModelName = meta.manufacturer_info.manufacturer_model
    ds.DeviceSerialNumber = meta.manufacturer_info.device_serial
    ds.SoftwareVersions = meta.manufacturer_info.software_version

    # Study / Series / SOP
    ds.StudyInstanceUID = opt_ds.StudyInstanceUID
    ds.SeriesInstanceUID = generate_uid()
    ds.FrameOfReferenceUID = opt_ds.FrameOfReferenceUID
    ds.Modality = "SEG"
    try:
        ds.SeriesNumber = int(meta.series_info.series_id) + 1000
    except (TypeError, ValueError):
        ds.SeriesNumber = 1000
    ds.Laterality = meta.series_info.laterality
    ds.SeriesDescription = (
        f"{meta.series_info.description} Height Map Segmentation"
        if meta.series_info.description
        else "Height Map Segmentation"
    )
    ds.SOPClassUID = HeightMapSegmentationStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID

    # General Image / Height Map Segmentation Image Module
    ds.ImageType = ["DERIVED", "PRIMARY"]
    ds.ContentLabel = "HEIGHTMAP"
    ds.ContentDescription = "Retinal layer height map segmentation"
    ds.ContentCreatorName = "oct_converter"
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.SegmentationType = "HEIGHTMAP"
    ds.NumberOfFrames = len(layers)
    ds.Rows = num_bscans
    ds.Columns = width
    ds.InstanceNumber = 1

    # Floating Point Image Pixel Module PS3.3 C.7.6.24
    ds.BitsAllocated = 32
    ds.FloatPixelPaddingValue = HEIGHTMAP_PADDING_VALUE
    # Keep padding range a single value outside [0, OPT.Rows]
    ds.FloatPixelPaddingRangeLimit = HEIGHTMAP_PADDING_VALUE

    set_content_date_time(ds)
    ds.AcquisitionDateTime = format_acquisition_datetime(
        meta.series_info.acquisition_date
    )

    # Segment Sequence
    segment_seq = []
    algorithm_name = (
        meta.manufacturer_info.manufacturer_model
        or meta.manufacturer_info.manufacturer
        or "oct_converter"
    )
    for idx, layer in enumerate(layers, start=1):
        seg = Dataset()
        seg.SegmentNumber = idx
        seg.SegmentLabel = layer.code.label
        seg.SegmentAlgorithmType = "AUTOMATIC"
        seg.SegmentAlgorithmName = str(algorithm_name)
        algo_id = Dataset()
        algo_id.AlgorithmName = str(algorithm_name)
        algo_id.AlgorithmVersion = version
        algo_id.AlgorithmFamilyCodeSequence = [
            _code_dataset("DCM", "123103", "Edge Detection")
        ]
        seg.SegmentationAlgorithmIdentificationSequence = [algo_id]
        seg.SegmentedPropertyCategoryCodeSequence = [
            _code_dataset(
                layer.code.category_scheme,
                layer.code.category_value,
                layer.code.category_meaning,
            )
        ]
        seg.SegmentedPropertyTypeCodeSequence = [
            _code_dataset(
                layer.code.type_scheme,
                layer.code.type_value,
                layer.code.type_meaning,
            )
        ]
        segment_seq.append(seg)
    ds.SegmentSequence = segment_seq

    # Dimension organization (minimal)
    dim_uid = generate_uid()
    dim_org = Dataset()
    dim_org.DimensionOrganizationUID = dim_uid
    ds.DimensionOrganizationSequence = [dim_org]
    dim_index = Dataset()
    dim_index.DimensionOrganizationUID = dim_uid
    dim_index.DimensionIndexPointer = (0x0062, 0x000B)  # Referenced Segment Number
    dim_index.FunctionalGroupPointer = (0x0062, 0x000A)  # Segment Identification Seq
    ds.DimensionIndexSequence = [dim_index]

    # Shared functional groups: Pixel Measures, Derivation Image, RWVM, Plane Orientation
    shared = Dataset()

    pm = Dataset()
    pm.PixelSpacing = [slice_thickness, opt_col_spacing]
    shared.PixelMeasuresSequence = [pm]

    if num_bscans > 1:
        po = Dataset()
        # Heightmap plane is orthogonal to OPT B-scans: rows along slice, cols along OPT cols
        # OPT orientation is [row_dir, col_dir]; heightmap row ~ OPT slice (Z), col ~ OPT col
        shared.PlaneOrientationSequence = [
            Dataset()
        ]
        # Approximate: row direction along patient Z of OPT stack, col along OPT column
        shared.PlaneOrientationSequence[0].ImageOrientationPatient = [
            0,
            0,
            1,
            image_orientation[3],
            image_orientation[4],
            image_orientation[5],
        ]

    # Derivation Image Functional Group
    purpose = _code_dataset(
        "DCM", "121322", "Source Image for Image Processing Operation"
    )
    derivation_code = _code_dataset("DCM", "113076", "Segmentation")
    source = Dataset()
    source.ReferencedSOPClassUID = opt_ds.SOPClassUID
    source.ReferencedSOPInstanceUID = opt_ds.SOPInstanceUID
    source.PurposeOfReferenceCodeSequence = [purpose]
    deriv_item = Dataset()
    deriv_item.DerivationCodeSequence = [derivation_code]
    deriv_item.SourceImageSequence = [source]
    shared.DerivationImageSequence = [deriv_item]

    # Real World Value Mapping: pixel height -> mm
    rwvm = Dataset()
    rwvm.DoubleFloatRealWorldValueFirstValueMapped = 0.0
    rwvm.DoubleFloatRealWorldValueLastValueMapped = float(max(opt_rows, 1))
    rwvm.RealWorldValueIntercept = 0.0
    rwvm.RealWorldValueSlope = float(axial_spacing_mm)
    rwvm.LUTExplanation = "Axial distance from top of B-scan"
    measurement = Dataset()
    measurement.CodeValue = "mm"
    measurement.CodingSchemeDesignator = "UCUM"
    measurement.CodeMeaning = "mm"
    rwvm.MeasurementUnitsCodeSequence = [measurement]
    shared.RealWorldValueMappingSequence = [rwvm]

    ds.SharedFunctionalGroupsSequence = [shared]

    # Per-frame functional groups + float pixel data
    per_frame = []
    float_frames = []
    for idx, layer in enumerate(layers, start=1):
        fg = Dataset()
        # Segment Identification
        seg_id = Dataset()
        seg_id.ReferencedSegmentNumber = idx
        fg.SegmentIdentificationSequence = [seg_id]
        # Frame Content
        fc = Dataset()
        fc.DimensionIndexValues = [idx]
        fc.InStackPositionNumber = idx
        fc.StackID = "1"
        fg.FrameContentSequence = [fc]
        if num_bscans > 1:
            pp = Dataset()
            pp.ImagePositionPatient = [0, 0, 0]
            fg.PlanePositionSequence = [pp]
        per_frame.append(fg)
        float_frames.append(layer.data.astype(np.float32))

    ds.PerFrameFunctionalGroupsSequence = per_frame

    # Common Instance Reference: referenced OPT series
    ref_inst = Dataset()
    ref_inst.ReferencedSOPClassUID = opt_ds.SOPClassUID
    ref_inst.ReferencedSOPInstanceUID = opt_ds.SOPInstanceUID
    ref_series = Dataset()
    ref_series.SeriesInstanceUID = opt_ds.SeriesInstanceUID
    ref_series.ReferencedInstanceSequence = [ref_inst]
    ds.ReferencedSeriesSequence = [ref_series]

    pixel_stack = np.stack(float_frames, axis=0)
    ds.FloatPixelData = pixel_stack.astype("<f4").tobytes()
    ds.save_as(
        filepath, implicit_vr=False, little_endian=True, enforce_file_format=True
    )
    return filepath


def write_fundus_dicom(
    meta: DicomMetadata,
    frames: t.List[np.ndarray],
    filepath: Path,
    study_instance_uid: str | None = None,
    series_instance_uid: str | None = None,
    sop_instance_uid: str | None = None,
) -> FileDataset:
    """Writes required DICOM metadata and fundus pixel data to .dcm file.

    Args:
            meta: DICOM metadata information
            frames: list of frames of pixel data
            filepath: Path to where output file is being saved
            study_instance_uid: Optional shared Study Instance UID
            series_instance_uid: Optional Series Instance UID
            sop_instance_uid: Optional SOP Instance UID
    Returns:
            FileDataset of the written fundus instance
    """
    ds = opt_base_dicom(filepath)
    ds = populate_patient_info(ds, meta)
    ds = populate_manufacturer_info(ds, meta)
    ds = populate_opt_series(
        ds,
        meta,
        study_instance_uid=study_instance_uid,
        series_instance_uid=series_instance_uid,
        sop_instance_uid=sop_instance_uid,
    )
    ds.Modality = "OP"
    ds.SOPClassUID = OphthalmicPhotography16BitImageStorage
    ds.file_meta.MediaStorageSOPClassUID = OphthalmicPhotography16BitImageStorage
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds = populate_ocular_region(ds, meta)

    ds.PixelSpacing = meta.image_geometry.pixel_spacing
    ds.ImageOrientationPatient = meta.image_geometry.image_orientation

    # OPT Image Module PS3.3 C.8.17.7
    ds.ImageType = ["DERIVED", "SECONDARY"]
    enface_to_type = {
        "IR": "RED",
        "FA": "BLUE",
        "ICGA": "GREEN",
    }
    if ds.ProtocolName in enface_to_type:
        ds.ImageType.append(enface_to_type.get(ds.ProtocolName))
    ds.SamplesPerPixel = 1
    ds.AcquisitionDateTime = format_acquisition_datetime(
        meta.series_info.acquisition_date
    )
    ds.AcquisitionNumber = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    # Unsigned integer
    ds.PixelRepresentation = 0
    # Use 16 bit pixel
    ds.BitsAllocated = 16
    ds.BitsStored = ds.BitsAllocated
    ds.HighBit = ds.BitsAllocated - 1
    ds.SamplesPerPixel = 1
    ds.NumberOfFrames = 1

    # Multi-frame Functional Groups Module PS3.3 C.7.6.16
    set_content_date_time(ds)
    ds.InstanceNumber = 1
    pixel_data = _as_grayscale_uint16(frames)
    ds.Rows = pixel_data.shape[0]
    ds.Columns = pixel_data.shape[1]

    ds.PixelData = pixel_data.tobytes()
    ds.save_as(
        filepath, implicit_vr=False, little_endian=True, enforce_file_format=True
    )
    return ds


def _as_grayscale_uint16(frames: t.Any) -> np.ndarray:
    """Coerce fundus pixel input to a 2-D uint16 grayscale image.

    RGB / RGBA arrays (HWC or CHW) are reduced to luminance so MONOCHROME2
    PixelData length matches Rows x Columns. Plain 2-D arrays are cast only.
    """
    arr = np.asarray(frames)
    if arr.ndim == 2:
        gray = arr
    elif arr.ndim == 3 and arr.shape[-1] in (3, 4):
        rgb = arr[..., :3].astype(np.float32)
        gray = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    elif arr.ndim == 3 and arr.shape[0] in (3, 4):
        rgb = arr[:3].astype(np.float32)
        gray = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    else:
        raise ValueError(
            f"Expected 2-D grayscale or 3-channel fundus image, got shape {arr.shape}"
        )
    return np.ascontiguousarray(gray, dtype=np.uint16)


def write_color_fundus_dicom(
    meta: DicomMetadata,
    frames: t.List[np.ndarray],
    filepath: Path,
    study_instance_uid: str | None = None,
) -> Path:
    """Writes required DICOM metadata and RGB fundus pixel data to .dcm file.

    Args:
            meta: DICOM metadata information
            frames: list of frames of pixel data
            filepath: Path to where output file is being saved
            study_instance_uid: Optional shared Study Instance UID
    Returns:
            Path to created DICOM file
    """
    ds = opt_base_dicom(filepath)
    ds = populate_patient_info(ds, meta)
    ds = populate_manufacturer_info(ds, meta)
    ds = populate_opt_series(ds, meta, study_instance_uid=study_instance_uid)
    ds.Modality = "OP"
    ds.SOPClassUID = OphthalmicPhotography16BitImageStorage
    ds.file_meta.MediaStorageSOPClassUID = OphthalmicPhotography16BitImageStorage
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds = populate_ocular_region(ds, meta)

    ds.PixelSpacing = meta.image_geometry.pixel_spacing
    ds.ImageOrientationPatient = meta.image_geometry.image_orientation

    # OPT Image Module PS3.3 C.8.17.7
    ds.ImageType = ["DERIVED", "SECONDARY"]
    enface_to_type = {
        "IR": "RED",
        "FA": "BLUE",
        "ICGA": "GREEN",
    }
    if ds.ProtocolName in enface_to_type:
        ds.ImageType.append(enface_to_type.get(ds.ProtocolName))
    ds.SamplesPerPixel = 1
    ds.AcquisitionDateTime = format_acquisition_datetime(
        meta.series_info.acquisition_date
    )
    ds.AcquisitionNumber = 1
    ds.PhotometricInterpretation = "RGB"
    # Unsigned integer
    ds.PixelRepresentation = 0
    # Use 16 bit pixel
    ds.BitsAllocated = 16
    ds.BitsStored = ds.BitsAllocated
    ds.HighBit = ds.BitsAllocated - 1
    ds.SamplesPerPixel = 1
    ds.NumberOfFrames = 1

    # Multi-frame Functional Groups Module PS3.3 C.7.6.16
    set_content_date_time(ds)
    ds.InstanceNumber = 1

    pixel_data = np.array(frames).astype(np.uint16)
    ds.Rows = pixel_data.shape[0]
    ds.Columns = pixel_data.shape[1]

    ds.PixelData = pixel_data.tobytes()
    ds.save_as(
        filepath, implicit_vr=False, little_endian=True, enforce_file_format=True
    )
    return filepath


def create_dicom_from_oct(
    input_file: str,
    output_dir: str = None,
    rows: int = 1024,
    cols: int = 512,
    interlaced: bool = False,
    diskbuffered: bool = False,
    extract_scan_repeats: bool = False,
    scalex: float = 0.01,
    slice_thickness: float = 0.05,
    apply_registration: bool = False,
) -> list:
    """Creates a DICOM file with the data parsed from
    the input file.

    Args:
            input_file: File with OCT data, .fda/.fds/.img/.e2e/.OCT
            output_dir: Output directory, will be created if
            not currently exists. Default None places file in
            current working directory.
            rows: If .img file, allows for manually setting rows
            cols: If .img file, allows for manually setting cols
            interlaced: If .img file, allows for setting interlaced
            diskbuffered: If Bioptigen .OCT, allows for setting diskbuffered
            extract_scan_repeats: If .e2e file, allows for extracting all scan repeats
            scalex: If .e2e file, allows for manually setting x scale (in mm)
            slice_thickness: If .e2e file, allows for manually setting z scale (in mm)
            apply_registration: If .e2e file, apply Heidelberg B-scan
                registration to OCT pixels and layer contours before writing
                DICOM. Defaults to False.

    Returns:
            list: list of Path(s) to DICOM file
    """
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path.cwd()

    file_suffix = input_file.split(".")[-1].lower()

    if file_suffix == "fds":
        files = create_dicom_from_fds(input_file, output_dir)
    elif file_suffix == "fda":
        files = create_dicom_from_fda(input_file, output_dir)
    elif file_suffix == "img":
        files = create_dicom_from_img(input_file, output_dir, rows, cols, interlaced)
    elif file_suffix == "oct":
        # Bioptigen and Octovue both use .OCT.
        # BOCT._validate on init can check if Bioptigen, else Optivue
        try:
            BOCT(input_file)
            files = create_dicom_from_boct(input_file, output_dir, diskbuffered)
        except (InvalidOCTReaderError, StreamError, UnicodeDecodeError, StringError):
            # if BOCT raises, treat as POCT
            files = create_dicom_from_poct(input_file, output_dir)
    elif file_suffix == "e2e":
        files = create_dicom_from_e2e(
            input_file,
            output_dir,
            extract_scan_repeats,
            scalex,
            slice_thickness,
            apply_registration=apply_registration,
        )
    else:
        raise TypeError(
            f"DICOM conversion for {file_suffix} is not supported. "
            "Currently supported filetypes are .e2e, .fds, .fda, .img, .OCT."
        )

    return files


def normalize_volume(vol: list[np.ndarray]) -> list[np.ndarray]:
    """Normalizes pixel intensities within a range of 0-100.

    Args:
        vol: List of frames
    Returns:
        Normalized list of frames
    """
    arr = np.array(vol)
    norm_vol = []
    diff_arr = arr.max() - arr.min()
    for i in arr:
        temp = ((i - arr.min()) / diff_arr) * 100
        norm_vol.append(temp)
    return norm_vol


def create_dicom_from_boct(
    input_file: str,
    output_dir: str = None,
    diskbuffered: bool = False,
) -> list:
    """Creates DICOM file(s) with the data parsed from
    the input file.

    Args:
            input_file: Bioptigen OCT file
            output_dir: Output directory
            diskbuffered: If True, reduces memory usage by storing volume on disk using HDF5.

    Returns:
            list: List of path(s) to DICOM file(s)"""

    boct = BOCT(input_file)
    oct_volumes = boct.read_oct_volume(diskbuffered)
    if len(oct_volumes) == 0:
        raise ValueError("No OCT volumes found in OCT input file.")

    files = []

    for count, oct in enumerate(oct_volumes):
        meta = boct_dicom_metadata(oct)
        filename = f"{Path(input_file).stem}_{str(count)}.dcm"
        filepath = Path(output_dir, filename)
        file = write_opt_dicom(meta, oct.volume, filepath)
        files.append(filepath)

    return files


def create_dicom_from_e2e(
    input_file: str,
    output_dir: str = None,
    extract_scan_repeats: bool = False,
    scalex: float = 0.01,
    slice_thickness: float = 0.05,
    apply_registration: bool = False,
) -> list:
    """Creates DICOM file(s) with the data parsed from
    the input file.

    Args:
            input_file: E2E file with OCT data
            output_dir: Output directory
            extract_scan_repeats: If True, will extract all scan repeats
            scalex: Manually set scale of x axis
            slice_thickness: Manually set scale of z axis
            apply_registration: Apply Heidelberg B-scan registration to
                OCT pixels and contours before writing. Defaults to False.

    Returns:
            list: List of path(s) to DICOM file(s)
    """
    e2e = E2E(input_file)
    oct_volumes = e2e.read_oct_volume(
        scalex=scalex,
        slice_thickness=slice_thickness,
        apply_registration=apply_registration,
    )
    fundus_images = e2e.read_fundus_image(
        extract_scan_repeats=extract_scan_repeats, scalex=scalex
    )
    if len(oct_volumes) == 0 and len(fundus_images) == 0:
        raise ValueError("No OCT volumes or fundus images found in e2e input file.")

    files = []
    # Map series key -> fundus FileDataset for Ophthalmic Frame Location
    fundus_by_id: dict[str, Dataset] = {}
    # Shared Study UID per E2E file
    study_uid = generate_uid()

    if len(fundus_images) > 0:
        for count, fundus in enumerate(fundus_images):
            meta = e2e_dicom_metadata(fundus)
            filename = f"{Path(input_file).stem}_fundus_{str(count)}.dcm"
            filepath = Path(output_dir, filename)
            fundus_ds = write_fundus_dicom(
                meta, fundus.image, filepath, study_instance_uid=study_uid
            )
            files.append(filepath)
            if fundus.image_id:
                # Strip trailing underscores used for scan-repeat disambiguation
                key = fundus.image_id.rstrip("_")
                fundus_by_id.setdefault(key, fundus_ds)
                fundus_by_id[fundus.image_id] = fundus_ds

    if len(oct_volumes) > 0:
        for count, oct in enumerate(oct_volumes):
            meta = e2e_dicom_metadata(oct)
            for_uid = generate_uid()
            filename = f"{Path(input_file).stem}_oct_{str(count)}.dcm"
            filepath = Path(output_dir, filename)
            fundus_ds = None
            if oct.volume_id:
                fundus_ds = fundus_by_id.get(oct.volume_id) or fundus_by_id.get(
                    oct.volume_id.rstrip("_")
                )
            # Fallback: single fundus for single OCT
            if fundus_ds is None and len(fundus_by_id) == 1:
                fundus_ds = next(iter(fundus_by_id.values()))
            opt_ds = write_opt_dicom(
                meta,
                oct.volume,
                filepath,
                study_instance_uid=study_uid,
                frame_of_reference_uid=for_uid,
                fundus_ds=fundus_ds,
            )
            files.append(filepath)

            if oct.contours:
                # Axial spacing is scaley (E2E pixel_spacing[1]).
                axial_mm = None
                if oct.pixel_spacing and len(oct.pixel_spacing) >= 2:
                    axial_mm = float(oct.pixel_spacing[1])
                seg_filename = f"{Path(input_file).stem}_seg_{str(count)}.dcm"
                seg_filepath = Path(output_dir, seg_filename)
                seg_path = write_heightmap_seg_dicom(
                    meta,
                    oct.contours,
                    opt_ds,
                    seg_filepath,
                    axial_spacing_mm=axial_mm,
                )
                if seg_path is not None:
                    files.append(seg_path)

    return files


def create_dicom_from_fda(
    input_file: str,
    output_dir: str,
) -> list:
    """Creates DICOM file(s) with the data parsed from
    the input file.

    When layer contours are present on the OCT volume, also writes a Height
    Map Segmentation companion (``{stem}_seg.dcm``) sharing Study and Frame
    of Reference UIDs with the OPT volume.

    Args:
            input_file: FDA file with OCT data
            output_dir: Output directory

    Returns:
            list: List of path(s) to DICOM file(s)
    """
    files = []
    fda = FDA(input_file)
    oct = fda.read_oct_volume()
    meta = fda_dicom_metadata(oct)
    study_uid = generate_uid()
    for_uid = generate_uid()
    output_filename = f"{Path(input_file).stem}.dcm"
    filepath = Path(output_dir, output_filename)
    opt_ds = write_opt_dicom(
        meta,
        oct.volume,
        filepath,
        study_instance_uid=study_uid,
        frame_of_reference_uid=for_uid,
    )
    files.append(filepath)

    # Write SEG before fundus mutates image_geometry.pixel_spacing.
    if oct.contours:
        axial_mm = None
        if oct.pixel_spacing and len(oct.pixel_spacing) >= 3:
            axial_mm = float(oct.pixel_spacing[2])
        seg_filepath = Path(output_dir, f"{Path(input_file).stem}_seg.dcm")
        seg_path = write_heightmap_seg_dicom(
            meta,
            oct.contours,
            opt_ds,
            seg_filepath,
            axial_spacing_mm=axial_mm,
        )
        if seg_path is not None:
            files.append(seg_path)

    # Attempt to parse fundus images
    fundus = fda.read_fundus_image()
    if fundus:
        output_filename = f"{Path(input_file).stem}_fundus.dcm"
        filepath = Path(output_dir, output_filename)
        meta.image_geometry.pixel_spacing = [1, 1]
        file = write_color_fundus_dicom(
            meta, fundus.image, filepath, study_instance_uid=study_uid
        )
        files.append(file)

    fundus_grayscale = fda.read_fundus_image_gray_scale()
    if fundus_grayscale:
        output_filename = f"{Path(input_file).stem}_fundus_grayscale.dcm"
        filepath = Path(output_dir, output_filename)
        meta.image_geometry.pixel_spacing = [1, 1]
        write_fundus_dicom(
            meta,
            fundus_grayscale.image,
            filepath,
            study_instance_uid=study_uid,
        )
        files.append(filepath)

    return files


def create_dicom_from_fds(
    input_file: str,
    output_dir: str,
) -> list:
    """Creates DICOM file(s) with the data parsed from
    the input file.

    Args:
            input_file: FDS file with OCT data
            output_dir: Output directory

    Returns:
            list: List of path(s) to DICOM file(s)
    """
    files = []
    fds = FDS(input_file)
    oct = fds.read_oct_volume()
    meta = fds_dicom_metadata(oct)
    output_filename = f"{Path(input_file).stem}.dcm"
    filepath = Path(output_dir, output_filename)
    file = write_opt_dicom(meta, oct.volume, filepath)
    files.append(filepath)

    # Attempt to parse fundus images
    fundus = fds.read_fundus_image()
    if fundus:
        output_filename = f"{Path(input_file).stem}_fundus.dcm"
        filepath = Path(output_dir, output_filename)
        file = write_color_fundus_dicom(meta, fundus.image, filepath)
        files.append(file)

    return files


def create_dicom_from_img(
    input_file: str,
    output_dir: str,
    rows: int = 1024,
    cols: int = 512,
    interlaced: bool = False,
) -> Path:
    """Creates a DICOM file with the data parsed from
    the input file.

    Args:
            input_file: .img file with OCT data
            output_dir: Output directory
            rows: Optional, for manually setting rows. Default 1024.
            cols: Optional, for manually setting cols. Default 512.
            interlaced: Optional, for setting interlaced. Default False.

    Returns:
            list: List of path(s) to DICOM file(s)
    """
    img = IMG(input_file)
    oct = img.read_oct_volume(rows, cols, interlaced)
    meta = img_dicom_metadata(oct)
    output_filename = f"{Path(input_file).stem}.dcm"
    filepath = Path(output_dir, output_filename)
    file = write_opt_dicom(meta, oct.volume, filepath)
    return [filepath]


def create_dicom_from_poct(
    input_file: str,
    output_dir: str,
) -> list:
    """Creates DICOM file(s) with the data parsed from
    the input file.

    Args:
            input_file: File with POCT data
            output_dir: Output directory

    Returns:
            list: List of path(s) to DICOM file(s)
    """
    poct = POCT(input_file)
    octs = poct.read_oct_volume()
    files = []
    for count, oct in enumerate(octs):
        meta = poct_dicom_metadata(oct)
        filename = f"{Path(input_file).stem}_{str(count)}.dcm"
        filepath = Path(output_dir, filename)
        file = write_opt_dicom(meta, oct.volume, filepath)
        files.append(filepath)

    return files
