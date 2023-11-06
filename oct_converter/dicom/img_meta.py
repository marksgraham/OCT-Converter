from __future__ import annotations

from datetime import datetime

from oct_converter.dicom.metadata import (
    DicomMetadata,
    ImageGeometry,
    ManufacturerMeta,
    OCTDetectorType,
    OCTImageParams,
    OPTAcquisitionDevice,
    OPTAnatomyStructure,
    PatientMeta,
    SeriesMeta,
)
from oct_converter.image_types import OCTVolumeWithMetaData


def img_patient_meta(patient_id: str = "") -> PatientMeta:
    """Creates PatientMeta populated with id if known from filename

    Args:
        patient_id: Patient ID, parsed from filename
    Returns:
        PatientMeta: Empty (or mostly empty) PatientMeta
    """
    patient = PatientMeta()

    patient.first_name = ""
    patient.last_name = ""
    patient.patient_id = patient_id
    patient.patient_sex = ""
    patient.patient_dob = None

    return patient


def img_series_meta(
    acquisition_date: datetime | None = None,
    laterality: str = "",
) -> SeriesMeta:
    """Creates SeriesMeta popualted with aquisition_date and
    laterality if known

    Args:
        acquisition_date: Date of acquisition, parsed from filename
        laterality: R or L, parsed from filename OD or OS
    Returns:
        SeriesMeta: Mostly empty SeriesMeta
    """
    series = SeriesMeta()

    series.study_id = ""
    series.series_id = 0
    series.laterality = laterality
    series.acquisition_date = acquisition_date
    series.opt_anatomy = OPTAnatomyStructure.Retina

    return series


def img_manu_meta() -> ManufacturerMeta:
    """Because img file contains no manufacture data,
    creates ManufacturerMeta with only manufacturer.

    Args:
        None
    Returns:
        ManufacturerMeta: Mostly empty ManufacturerMeta
    """
    manufacture = ManufacturerMeta()

    manufacture.manufacturer = "Zeiss"
    manufacture.manufacturer_model = ""
    manufacture.device_serial = ""
    manufacture.software_version = ""

    return manufacture


def img_image_geom() -> ImageGeometry:
    """Creates ImageGeometry with generic values

    Args:
        None
    Returns:
        ImageGeometry: Geometry data populated with generic values
    """
    image_geom = ImageGeometry()
    image_geom.pixel_spacing = [0.002, 0.002]
    image_geom.slice_thickness = 0.004
    image_geom.image_orientation = [1, 0, 0, 0, 1, 0]

    return image_geom


def img_image_params() -> OCTImageParams:
    """Creates OCTImageParams specific to Zeiss

    Args:
        None
    Returns:
        OCTImageParams: Image params populated with img defaults
    """
    image_params = OCTImageParams()
    image_params.opt_acquisition_device = OPTAcquisitionDevice.OCTScanner
    image_params.DetectorType = OCTDetectorType.CCD
    image_params.IlluminationWaveLength = 830
    image_params.IlluminationPower = 800
    image_params.IlluminationBandwidth = 50
    image_params.DepthSpatialResolution = 6
    image_params.MaximumDepthDistortion = 0.5
    image_params.AlongscanSpatialResolution = []
    image_params.MaximumAlongscanDistortion = []
    image_params.AcrossscanSpatialResolution = []
    image_params.MaximumAcrossscanDistortion = []

    return image_params


def img_dicom_metadata(oct: OCTVolumeWithMetaData) -> DicomMetadata:
    """Creates DicomMetadata and populates each module

    Args:
        oct: OCTVolumeWithMetaData created by img reader
    Returns:
        DicomMetadata: Populated DicomMetadata created with Zeiss defaults
        and information extracted from filename if able
    """
    meta = DicomMetadata
    meta.patient_info = img_patient_meta(oct.patient_id)
    meta.series_info = img_series_meta(oct.acquisition_date, oct.laterality)
    meta.manufacturer_info = img_manu_meta()
    meta.image_geometry = img_image_geom()
    meta.oct_image_params = img_image_params()

    return meta
