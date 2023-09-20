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


def e2e_patient_meta(oct: OCTVolumeWithMetaData) -> PatientMeta:
    """Creates PatientMeta from e2e info stored in OCTVolumeWithMetaData

    Args:
        oct: OCTVolumeWithMetaData obj with patient info attributes
    Returns:
        PatientMeta: Patient metadata populated by oct
    """
    patient = PatientMeta()

    patient.first_name = oct.first_name
    patient.last_name = oct.surname
    # E2E has conflicting patient_ids, between the one in the
    # patient chunk and the chunk and subdirectory headers.
    # The patient chunk data is used here.
    patient.patient_id = oct.patient_id
    patient.patient_sex = oct.sex
    patient.patient_dob = oct.DOB

    return patient


def e2e_series_meta(oct: OCTVolumeWithMetaData) -> SeriesMeta:
    """Creates SeriesMeta from e2e info stored in OCTVolumeWithMetaData

    Args:
        oct: OCTVolumeWithMetaData obj with series info attributes
    Returns:
        SeriesMeta: Series metadata populated by oct
    """
    patient_id, study_id, series_id = oct.volume_id.split("_")
    series = SeriesMeta()

    series.study_id = study_id
    series.series_id = series_id
    series.laterality = oct.laterality
    series.acquisition_date = oct.acquisition_date
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

    manufacture.manufacturer = "Heidelberg"
    manufacture.manufacturer_model = ""
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
    image_geom.pixel_spacing = [pixel_spacing[0], pixel_spacing[1]]
    # ScaleX, ScaleY
    # ScaleY seems to be found, and also constant.
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
    image_params.AlongscanSpatialResolution = ""
    image_params.MaximumAlongscanDistortion = ""
    image_params.AcrossscanSpatialResolution = ""
    image_params.MaximumAcrossscanDistortion = ""

    return image_params


def e2e_dicom_metadata(oct: OCTVolumeWithMetaData) -> DicomMetadata:
    """Creates DicomMetadata and populates each module

    Args:
        oct: OCTVolumeWithMetaData created by the E2E reader
    Returns:
        DicomMetadata: Populated DicomMetadata created with OCT metadata
    """
    meta = DicomMetadata
    meta.patient_info = e2e_patient_meta(oct)
    meta.series_info = e2e_series_meta(oct)
    meta.manufacturer_info = e2e_manu_meta()
    meta.image_geometry = e2e_image_geom(oct.pixel_spacing)
    meta.oct_image_params = e2e_image_params()

    return meta
