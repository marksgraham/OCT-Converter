from __future__ import annotations

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
from oct_converter.image_types import FundusImageWithMetaData, OCTVolumeWithMetaData


def e2e_patient_meta(meta: dict) -> PatientMeta:
    """Creates PatientMeta from e2e info stored in raw metadata

    Args:
        meta: Nested dictionary of metadata accumulated by the E2E reader
    Returns:
        PatientMeta: Patient metadata populated by oct
    """
    patient = PatientMeta()

    patient_data = meta.get("patient_data", [{}])

    patient.first_name = patient_data[0].get("first_name")
    patient.last_name = patient_data[0].get("surname")
    patient.patient_id = patient_data[0].get("patient_id")
    patient.patient_sex = patient_data[0].get("sex")
    # TODO patient.patient_dob
    # Currently, E2E's patient_dob is incorrect, see
    # the E2E reader for more context.

    return patient


def e2e_series_meta(id, laterality, acquisition_date) -> SeriesMeta:
    """Creates SeriesMeta from info parsed by the E2E reader

    Args:
        id: Equivalent to oct.volume_id or fundus.image_id
        laterality: R or L, from image.laterality
        acquisition_date: Scan date for OCT, or None for fundus
    Returns:
        SeriesMeta: Series metadata populated by oct
    """
    patient_db_id, study_id, series_id = id.split("_")
    series = SeriesMeta()

    series.study_id = study_id
    series.series_id = series_id
    series.laterality = laterality
    series.acquisition_date = acquisition_date
    series.opt_anatomy = OPTAnatomyStructure.Retina

    return series


def e2e_manu_meta() -> ManufacturerMeta:
    """Creates ManufacturerMeta with Heidelberg defaults.

    Args:
        None
    Returns:
        ManufacturerMeta: Manufacture metadata module
    """
    manufacture = ManufacturerMeta()

    manufacture.manufacturer = "Heidelberg Engineering"
    manufacture.manufacturer_model = "Spectralis"
    manufacture.device_serial = ""
    manufacture.software_version = ""

    return manufacture


def e2e_image_geom(pixel_spacing: list) -> ImageGeometry:
    """Creates ImageGeometry from E2E metadata

    Args:
        pixel_spacing: Pixel spacing identified by E2E reader
    Returns:
        ImageGeometry: Geometry data populated by pixel_spacing
    """
    image_geom = ImageGeometry()
    image_geom.pixel_spacing = [pixel_spacing[1], pixel_spacing[0]]
    image_geom.slice_thickness = pixel_spacing[2]
    image_geom.image_orientation = [1, 0, 0, 0, 1, 0]

    return image_geom


def e2e_image_params() -> OCTImageParams:
    """Creates OCTImageParams specific to E2E

    Args:
        None
    Returns:
        OCTImageParams: Image params populated with E2E defaults
    """
    image_params = OCTImageParams()
    image_params.opt_acquisition_device = OPTAcquisitionDevice.OCTScanner
    image_params.DetectorType = OCTDetectorType.CCD
    image_params.IlluminationWaveLength = 880
    image_params.IlluminationPower = 1200
    image_params.IlluminationBandwidth = 50
    image_params.DepthSpatialResolution = 7
    image_params.MaximumDepthDistortion = 0.5
    image_params.AlongscanSpatialResolution = 13
    image_params.MaximumAlongscanDistortion = 0.5
    image_params.AcrossscanSpatialResolution = 13
    image_params.MaximumAcrossscanDistortion = 0.5

    return image_params


def e2e_dicom_metadata(
    image: FundusImageWithMetaData | OCTVolumeWithMetaData,
) -> DicomMetadata:
    """Creates DicomMetadata for oct or fundus image and populates each module

    Args:
        image: Oct or Fundus image type created by the E2E reader
    Returns:
        DicomMetadata: Populated DicomMetadata created with fundus or oct metadata
    """

    meta = DicomMetadata
    meta.patient_info = e2e_patient_meta(image.metadata)
    meta.manufacturer_info = e2e_manu_meta()
    meta.oct_image_params = e2e_image_params()
    if type(image) == OCTVolumeWithMetaData:
        meta.series_info = e2e_series_meta(
            image.volume_id, image.laterality, image.acquisition_date
        )
        meta.image_geometry = e2e_image_geom(image.pixel_spacing)
    else:  # type(image) == FundusImageWithMetaData
        meta.series_info = e2e_series_meta(image.image_id, image.laterality, None)
        meta.image_geometry = e2e_image_geom([1, 1, 1])

    return meta
