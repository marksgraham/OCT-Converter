import dataclasses
import datetime
import enum
import typing as t
from dataclasses import field


class OPTAcquisitionDevice(enum.Enum):
    """OPT Acquisition Device enumeration.

    Contains code designator, code value and code meaning for each entry.
    """

    OCTScanner = ("SRT", "A-00FBE", "Optical Coherence Tomography Scanner")
    RetinalThicknessAnalyzer = ("SRT", "R-FAB5A", "Retinal Thickness Analyzer")
    ConfocalScanningLaserOphthalmoscope = (
        "SRT",
        "A-00E8B",
        "Confocal Scanning Laser Ophthalmoscope",
    )
    ScheimpflugCamera = ("DCM", "111626", "Scheimpflug Camera")
    ScanningLaserPolarimeter = ("SRT", "A-00E8C", "Scanning Laser Polarimeter")
    ElevationBasedCornealTomographer = (
        "DCM",
        "111945",
        "Elevation-based corneal tomographer",
    )
    ReflectionBasedCornealTopographer = (
        "DCM",
        "111946",
        "Reflection-based corneal topographer",
    )
    InterferometryBasedCornealTomographer = (
        "DCM",
        "111947",
        "Interferometry-based corneal tomographer",
    )
    Unspecified = ("OCT-converter", "D-0001", "Unspecified scanner")


class OPTAnatomyStructure(enum.Enum):
    """OPT Anatomy enumeration.

    Contains code designator, code value and code meaning for each entry.
    """

    AnteriorChamberOfEye = ("SRT", "T-AA050", "Anterior chamber of eye")
    BothEyes = ("SRT", "T-AA180", "Both eyes")
    ChoroidOfEye = ("SRT", "T-AA310", "Choroid of eye")
    CiliaryBody = ("SRT", "T-AA400", "Ciliary body")
    Conjunctiva = ("SRT", "T-AA860", "Conjunctiva")
    Cornea = ("SRT", "T-AA200", "Cornea")
    Eye = ("SRT", "T-AA000", "Eye")
    Eyelid = ("SRT", "T-AA810", "Eyelid")
    FoveaCentralis = ("SRT", "T-AA621", "Fovea centralis")
    Iris = ("SRT", "T-AA500", "Iris")
    LacrimalCaruncle = ("SRT", "T-AA862", "Lacrimal caruncle")
    LacrimalGland = ("SRT", "T-AA910", "Lacrimal gland")
    LacrimalSac = ("SRT", "T-AA940", "Lacrimal sac")
    Lens = ("SRT", "T-AA700", "Lens")
    LowerEyeLid = ("SRT", "T-AA830", "Lower Eyelid")
    OphthalmicArtery = ("SRT", "T-45400", "Ophthalmic artery")
    OpticNerveHead = ("SRT", "T-AA630", "Optic nerve head")
    Retina = ("SRT", "T-AA610", "Retina")
    Sclera = ("SRT", "T-AA110", "Sclera")
    UpperEyeLid = ("SRT", "T-AA820", "Upper Eyelid")
    Unspecified = ("OCT-converter", "A-0001", "Unspecified anatomy")


class OCTDetectorType(enum.Enum):
    CCD = "CCD"
    CMOS = "CMOS"
    PHOTO = "PHOTO"
    INT = "INT"
    Unknown = "UNKNOWN"


@dataclasses.dataclass
class PatientMeta:
    # Patient Info
    first_name: str = ""
    last_name: str = ""
    patient_id: str = ""
    patient_sex: str = ""
    patient_dob: t.Optional[datetime.datetime] = None


@dataclasses.dataclass
class SeriesMeta:
    # Study and Series
    study_id: str = ""
    series_id: str = ""
    laterality: str = ""
    acquisition_date: t.Optional[datetime.datetime] = None
    # Anatomy
    opt_anatomy: OPTAnatomyStructure = OPTAnatomyStructure.Unspecified


@dataclasses.dataclass
class ManufacturerMeta:
    # Manufacturer info
    manufacturer: str = ""
    manufacturer_model: str = "unknown"
    device_serial: str = "unknown"
    software_version: str = "unknown"


@dataclasses.dataclass
class ImageGeometry:
    # Image geometry info
    pixel_spacing: list[float] = field(default_factory=list)
    slice_thickness: float = 1.0
    image_orientation: list[float] = field(default_factory=list)


@dataclasses.dataclass
class OCTImageParams:
    # PS3.3 C.8.17.9
    opt_acquisition_device: OPTAcquisitionDevice = OPTAcquisitionDevice.Unspecified
    DetectorType: OCTDetectorType = OCTDetectorType.Unknown
    IlluminationWaveLength: t.Optional[float] = None
    IlluminationPower: t.Optional[float] = None
    IlluminationBandwidth: t.Optional[float] = None
    DepthSpatialResolution: t.Optional[float] = None
    MaximumDepthDistortion: t.Optional[float] = None
    AlongscanSpatialResolution: t.Optional[float] = None
    MaximumAlongscanDistortion: t.Optional[float] = None
    AcrossscanSpatialResolution: t.Optional[float] = None
    MaximumAcrossscanDistortion: t.Optional[float] = None

    # NOTE: Could eventually include C.8.17.8 Acquisition Params.


@dataclasses.dataclass
class DicomMetadata:
    patient_info: PatientMeta
    series_info: SeriesMeta
    manufacturer_info: ManufacturerMeta

    image_geometry: ImageGeometry
    oct_image_params: OCTImageParams
