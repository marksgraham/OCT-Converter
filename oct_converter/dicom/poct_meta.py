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


def poct_series_meta(poct: OCTVolumeWithMetaData) -> SeriesMeta:
    """Creates SeriesMeta from Optovue OCT metadata

    Args:
        poct: OCTVolumeWithMetaData with laterality and acquisition_date attributes
    Returns:
        SeriesMeta: Series metadata populated with laterality and acquisition_date
    """

    series = SeriesMeta()

    series.study_id = ""
    series.series_id = 0
    series.laterality = poct.laterality
    series.acquisition_date = poct.acquisition_date
    series.opt_anatomy = OPTAnatomyStructure.Retina

    return series


def poct_manu_meta() -> ManufacturerMeta:
    """Creates base ManufacturerMeta for Optovue

    Args:
        None
    Returns:
        ManufacturerMeta: base Optovue manufacture metadata
    """

    manufacture = ManufacturerMeta()

    manufacture.manufacturer = "Optovue"
    manufacture.manufacturer_model = ""
    manufacture.device_serial = ""
    manufacture.software_version = ""

    return manufacture


def poct_image_geom(pixel_spacing: list) -> ImageGeometry:
    """Creates ImageGeometry from Optovue OCT metadata

    Args:
        pixel_spacing: Pixel spacing calculated in the poct reader
    Returns:
        ImageGeometry: Geometry data populated by pixel_spacing
    """
    image_geom = ImageGeometry()
    image_geom.pixel_spacing = pixel_spacing
    image_geom.slice_thickness = 0.02  # Placeholder value
    image_geom.image_orientation = [1, 0, 0, 0, 1, 0]

    return image_geom


def poct_image_params() -> OCTImageParams:
    """Creates OCTImageParams specific to Optovue

    Args:
        None
    Returns:
        OCTImageParams: Image params populated with Optovue defaults
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


def poct_dicom_metadata(poct: OCTVolumeWithMetaData) -> DicomMetadata:
    """Creates DicomMetadata and populates each module

    Args:
        oct: OCTVolumeWithMetaData created by the poct reader
    Returns:
        DicomMetadata: Populated DicomMetadata created with OCT metadata
    """
    meta = DicomMetadata
    meta.patient_info = PatientMeta()
    meta.series_info = poct_series_meta(poct)
    meta.manufacturer_info = poct_manu_meta()
    meta.image_geometry = poct_image_geom(poct.pixel_spacing)
    meta.oct_image_params = poct_image_params()

    return meta
