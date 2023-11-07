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


def boct_series_meta(boct: OCTVolumeWithMetaData) -> SeriesMeta:
    """Creates SeriesMeta from Bioptigen OCT metadata

    Args:
        boct: OCTVolumeWithMetaData with laterality and acquisition_date attributes
    Returns:
        SeriesMeta: Series metadata populated with laterality and acquisition_date
    """
    series = SeriesMeta()

    series.study_id = ""
    series.series_id = 0
    series.laterality = boct.laterality
    series.acquisition_date = boct.acquisition_date
    series.opt_anatomy = OPTAnatomyStructure.Retina

    return series


def boct_manu_meta() -> ManufacturerMeta:
    """Creates base ManufacturerMeta for Bioptigen

    Args:
        None
    Returns:
        ManufacturerMeta: base Bioptigen manufacture metadata
    """

    manufacture = ManufacturerMeta()

    manufacture.manufacturer = "Bioptigen"
    manufacture.manufacturer_model = ""
    manufacture.device_serial = ""
    manufacture.software_version = ""

    return manufacture


def boct_image_geom() -> ImageGeometry:
    """Creates ImageGeometry from Bioptigen OCT metadata

    Args:
        pixel_spacing: Pixel spacing calculated in the boct reader
    Returns:
        ImageGeometry: Geometry data populated by pixel_spacing
    """
    image_geom = ImageGeometry()
    image_geom.pixel_spacing = [0.02, 0.02]  # Placeholder value
    image_geom.slice_thickness = 0.2  # Placeholder value
    image_geom.image_orientation = [1, 0, 0, 0, 1, 0]

    return image_geom


def boct_image_params() -> OCTImageParams:
    """Creates OCTImageParams specific to Bioptigen

    Args:
        None
    Returns:
        OCTImageParams: Image params populated with Bioptigen defaults
    """
    image_params = OCTImageParams()
    image_params.opt_acquisition_device = OPTAcquisitionDevice.OCTScanner
    image_params.DetectorType = OCTDetectorType.CCD
    image_params.IlluminationWaveLength = 880
    image_params.IlluminationPower = 1200
    image_params.IlluminationBandwidth = 50
    image_params.DepthSpatialResolution = 7
    image_params.MaximumDepthDistortion = 0.5
    image_params.AlongscanSpatialResolution = []
    image_params.MaximumAlongscanDistortion = []
    image_params.AcrossscanSpatialResolution = []
    image_params.MaximumAcrossscanDistortion = []

    return image_params


def boct_dicom_metadata(boct: OCTVolumeWithMetaData) -> DicomMetadata:
    """Creates DicomMetadata and populates each module

    Args:
        oct: OCTVolumeWithMetaData created by the boct reader
    Returns:
        DicomMetadata: Populated DicomMetadata created with OCT metadata
    """
    meta = DicomMetadata
    meta.patient_info = PatientMeta()
    meta.series_info = boct_series_meta(boct)
    meta.manufacturer_info = boct_manu_meta()
    meta.image_geometry = boct_image_geom()
    meta.oct_image_params = boct_image_params()

    return meta
