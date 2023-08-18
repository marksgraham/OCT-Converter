from oct_converter.dicom.metadata import *
from datetime import datetime

from oct_converter.image_types import OCTVolumeWithMetaData

def fda_patient_meta(fds_metadata: dict) -> PatientMeta:
    patient_info = fds_metadata.get("patient_info_02") or fds_metadata.get("patient_info", {})
    sex_map = {1: "M", 2: "F", 3: "O", None: ""}
    patient = PatientMeta()

    patient.first_name = patient_info.get("first_name")
    patient.last_name = patient_info.get("last_name")
    patient.patient_id = patient_info.get("patient_id")
    patient.patient_sex = sex_map[patient_info.get("sex", None)]
    patient.patient_dob = datetime(*patient_info.get("birth_date")) if patient_info.get('birth_date')[0] != 0 else None

    return patient


def fda_series_meta(fds_metadata: dict) -> SeriesMeta:
    capture_info = fds_metadata.get("capture_info_02") or fds_metadata.get("capture_info", {})
    lat_map = {0: "R", 1: "L", None: ""}
    series = SeriesMeta()

    series.study_id = ""
    series.series_id = capture_info.get("session_id", "")
    series.laterality = lat_map[capture_info.get("eye", None)]
    series.acquisition_date = datetime(*capture_info.get('cap_date'))
    series.opt_anatomy = OPTAnatomyStructure.Retina

    return series


def fda_manu_meta(fds_metadata: dict, fds_header: dict) -> ManufacturerMeta:
    hw_info = fds_metadata.get("hw_info_03") or fds_metadata.get("hw_info_02") or fds_metadata.get("hw_info_01", {})
    manufacture = ManufacturerMeta()

    manufacture.manufacturer = "Topcon"
    manufacture.manufacturer_model = hw_info.get("model_name")
    manufacture.device_serial = hw_info.get("serial_number")
    manufacture.software_version = f"{fds_header.get('major_ver')}.{fds_header.get('minor_ver')}"

    return manufacture


def fda_image_geom(pixel_spacing: list) -> ImageGeometry:
    image_geom = ImageGeometry()
    image_geom.pixel_spacing = [pixel_spacing[2], pixel_spacing[0]]
    image_geom.slice_thickness = pixel_spacing[1]
    image_geom.image_orientation = [1, 0, 0, 0, 1, 0]

    return image_geom


def fda_image_params() -> OCTImageParams:
    image_params = OCTImageParams()
    image_params.opt_acquisition_device = OPTAcquisitionDevice.OCTScanner
    image_params.DetectorType = OCTDetectorType.CCD
    image_params.IlluminationWaveLength = 830
    image_params.IlluminationPower = 800
    image_params.IlluminationBandwidth = 50
    image_params.DepthSpatialResolution = 6
    image_params.MaximumDepthDistortion = 0.5
    image_params.AlongscanSpatialResolution = 20
    image_params.MaximumAlongscanDistortion = 0.5
    image_params.AcrossscanSpatialResolution = 20
    image_params.MaximumAcrossscanDistortion = 0.5

    return image_params


def fda_dicom_metadata(oct: OCTVolumeWithMetaData) -> DicomMetadata:
    meta = DicomMetadata
    meta.patient_info = fda_patient_meta(oct.metadata)
    meta.series_info = fda_series_meta(oct.metadata)
    meta.manufacturer_info = fda_manu_meta(oct.metadata, oct.header)
    meta.image_geometry = fda_image_geom(oct.pixel_spacing)
    meta.oct_image_params = fda_image_params()

    return meta