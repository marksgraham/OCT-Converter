import typing as t
from datetime import datetime
from importlib import metadata
from pathlib import Path

import numpy as np
from construct import StreamError
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import (
    ExplicitVRLittleEndian,
    OphthalmicTomographyImageStorage,
    generate_uid,
)

from oct_converter.dicom.boct_meta import boct_dicom_metadata
from oct_converter.dicom.e2e_meta import e2e_dicom_metadata
from oct_converter.dicom.fda_meta import fda_dicom_metadata
from oct_converter.dicom.fds_meta import fds_dicom_metadata
from oct_converter.dicom.img_meta import img_dicom_metadata
from oct_converter.dicom.metadata import DicomMetadata
from oct_converter.dicom.poct_meta import poct_dicom_metadata
from oct_converter.exceptions import InvalidOCTReaderError
from oct_converter.readers import BOCT, E2E, FDA, FDS, IMG, POCT

# Deterministic implementation UID based on package name and version
version = metadata.version("oct_converter")
implementation_uid = generate_uid(entropy_srcs=["oct_converter", version])


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
    ds.is_little_endian = True
    ds.is_implicit_VR = False  # Explicit VR
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
    ds.PatientName = f"{meta.patient_info.last_name}^{meta.patient_info.first_name}"
    ds.PatientID = meta.patient_info.patient_id
    ds.PatientSex = meta.patient_info.patient_sex
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


def populate_opt_series(ds: Dataset, meta: DicomMetadata) -> Dataset:
    """Populates study and series modules, PS3.3 C.7.2.1, PS3.3 C.7.3.1,
    PS3.3 C.8.17.6, and PS3.3 C.12.1

    Args:
            ds: current dataset
            meta: DICOM metadata information
    Returns:
            ds: Dataset, updated with study and series information
    """
    # General study module PS3.3 C.7.2.1
    # Deterministic StudyInstanceUID based on study ID
    # ds.StudyInstanceUID = generate_uid(entropy_srcs=[
    # 	# str(uuid.uuid4()),
    # 	str(meta.series_info.study_id)
    # ])

    # # General series module PS3.3 C.7.3.1
    # ds.SeriesInstanceUID = generate_uid(entropy_srcs=[
    # 	# str(uuid.uuid4()),
    # 	str(meta.series_info.series_id)
    # ])
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.Laterality = meta.series_info.laterality
    # Ophthalmic Tomography Series PS3.3 C.8.17.6
    ds.Modality = "OPT"
    ds.SeriesNumber = int(meta.series_info.series_id)

    # SOP Common module PS3.3 C.12.1
    ds.SOPClassUID = OphthalmicTomographyImageStorage
    ds.SOPInstanceUID = generate_uid()
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
    shared_ds[0].FrameAnatomySequence[0] = ds.AnatomicRegionSequence[0].copy()
    shared_ds[0].FrameAnatomySequence[0].FrameLaterality = meta.series_info.laterality
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
    meta: DicomMetadata, frames: t.List[np.ndarray], filepath: Path
) -> Path:
    """Writes required DICOM metadata and oct pixel data to .dcm file.

    Args:
            meta: DICOM metadata information
            frames: list of frames of pixel data
            filepath: Path to where output file is being saved
    Returns:
            Path to created DICOM file
    """
    ds = opt_base_dicom(filepath)
    ds = populate_patient_info(ds, meta)
    ds = populate_manufacturer_info(ds, meta)
    ds = populate_opt_series(ds, meta)
    ds = populate_ocular_region(ds, meta)
    ds = opt_shared_functional_groups(ds, meta)

    # TODO: Frame of reference if fundus image present

    # OPT Image Module PS3.3 C.8.17.7
    ds.ImageType = ["DERIVED", "SECONDARY"]
    ds.SamplesPerPixel = 1
    ds.AcquisitionDateTime = (
        meta.series_info.acquisition_date.strftime("%Y%m%d%H%M%S.%f")
        if meta.series_info.acquisition_date
        else ""
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
    dt = datetime.now()
    ds.ContentDate = dt.strftime("%Y%m%d")
    timeStr = dt.strftime("%H%M%S.%f")  # long format with micro seconds
    ds.ContentTime = timeStr
    ds.InstanceNumber = 1

    per_frame = []
    pixel_data_bytes = list()
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
        ipp = [0, 0, i * meta.image_geometry.slice_thickness]
        frame_fgs.PlanePositionSequence[0].ImagePositionPatient = ipp
        frame_fgs.FrameContentSequence = [Dataset()]
        frame_fgs.FrameContentSequence[0].InStackPositionNumber = i + 1
        frame_fgs.FrameContentSequence[0].StackID = "1"

        # Pixel data
        frame_dat = pixel_data[i, :, :]
        pixel_data_bytes.append(frame_dat.tobytes())
        per_frame.append(frame_fgs)
    ds.PerFrameFunctionalGroupsSequence = per_frame
    ds.PixelData = pixel_data.tobytes()
    ds.save_as(filepath)
    return filepath


def write_fundus_dicom(
    meta: DicomMetadata, frames: t.List[np.ndarray], filepath: Path
) -> Path:
    """Writes required DICOM metadata and fundus pixel data to .dcm file.

    Args:
            meta: DICOM metadata information
            frames: list of frames of pixel data
            filepath: Path to where output file is being saved
    Returns:
            Path to created DICOM file
    """
    ds = opt_base_dicom(filepath)
    ds = populate_patient_info(ds, meta)
    ds = populate_manufacturer_info(ds, meta)
    ds = populate_opt_series(ds, meta)
    ds.Modality = "OP"
    ds = populate_ocular_region(ds, meta)
    ds = opt_shared_functional_groups(ds, meta)

    # OPT Image Module PS3.3 C.8.17.7
    ds.ImageType = ["DERIVED", "SECONDARY"]
    ds.SamplesPerPixel = 1
    ds.AcquisitionDateTime = (
        meta.series_info.acquisition_date.strftime("%Y%m%d%H%M%S.%f")
        if meta.series_info.acquisition_date
        else ""
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
    dt = datetime.now()
    ds.ContentDate = dt.strftime("%Y%m%d")
    timeStr = dt.strftime("%H%M%S.%f")  # long format with micro seconds
    ds.ContentTime = timeStr
    ds.InstanceNumber = 1
    pixel_data = np.array(frames).astype(np.uint16)
    ds.Rows = pixel_data.shape[0]
    ds.Columns = pixel_data.shape[1]

    ds.PixelData = pixel_data.tobytes()
    ds.save_as(filepath)
    return filepath


def write_color_fundus_dicom(
    meta: DicomMetadata, frames: t.List[np.ndarray], filepath: Path
) -> Path:
    """Writes required DICOM metadata and RGB fundus pixel data to .dcm file.

    Args:
            meta: DICOM metadata information
            frames: list of frames of pixel data
            filepath: Path to where output file is being saved
    Returns:
            Path to created DICOM file
    """
    ds = opt_base_dicom(filepath)
    ds = populate_patient_info(ds, meta)
    ds = populate_manufacturer_info(ds, meta)
    ds = populate_opt_series(ds, meta)
    ds.Modality = "OP"
    ds = populate_ocular_region(ds, meta)
    ds = opt_shared_functional_groups(ds, meta)

    # OPT Image Module PS3.3 C.8.17.7
    ds.ImageType = ["DERIVED", "SECONDARY"]
    ds.SamplesPerPixel = 1
    ds.AcquisitionDateTime = (
        meta.series_info.acquisition_date.strftime("%Y%m%d%H%M%S.%f")
        if meta.series_info.acquisition_date
        else ""
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
    dt = datetime.now()
    ds.ContentDate = dt.strftime("%Y%m%d")
    timeStr = dt.strftime("%H%M%S.%f")  # long format with micro seconds
    ds.ContentTime = timeStr
    ds.InstanceNumber = 1

    pixel_data = np.array(frames).astype(np.uint16)
    ds.Rows = pixel_data.shape[0]
    ds.Columns = pixel_data.shape[1]

    ds.PixelData = pixel_data.tobytes()
    ds.save_as(filepath)
    return filepath


def create_dicom_from_oct(
    input_file: str,
    output_dir: str = None,
    rows: int = 1024,
    cols: int = 512,
    interlaced: bool = False,
    diskbuffered: bool = False,
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
        except (InvalidOCTReaderError, StreamError):
            # if BOCT raises, treat as POCT
            files = create_dicom_from_poct(input_file, output_dir)
    elif file_suffix == "e2e":
        files = create_dicom_from_e2e(input_file, output_dir)
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
        files.append(file)

    return files


def create_dicom_from_e2e(
    input_file: str,
    output_dir: str = None,
) -> list:
    """Creates DICOM file(s) with the data parsed from
    the input file.

    Args:
            input_file: E2E file with OCT data
            output_dir: Output directory

    Returns:
            list: List of path(s) to DICOM file(s)
    """
    e2e = E2E(input_file)
    oct_volumes = e2e.read_oct_volume()
    fundus_images = e2e.read_fundus_image()
    if len(oct_volumes) == 0 and len(fundus_images) == 0:
        raise ValueError("No OCT volumes or fundus images found in e2e input file.")

    files = []

    if len(fundus_images) > 0:
        for count, fundus in enumerate(fundus_images):
            meta = e2e_dicom_metadata(fundus)
            filename = f"{Path(input_file).stem}_fundus_{str(count)}.dcm"
            filepath = Path(output_dir, filename)
            file = write_fundus_dicom(meta, fundus.image, filepath)
            files.append(file)

    if len(oct_volumes) > 0:
        for count, oct in enumerate(oct_volumes):
            meta = e2e_dicom_metadata(oct)
            filename = f"{Path(input_file).stem}_oct_{str(count)}.dcm"
            filepath = Path(output_dir, filename)
            file = write_opt_dicom(meta, oct.volume, filepath)
            files.append(file)

    return files


def create_dicom_from_fda(
    input_file: str,
    output_dir: str,
) -> list:
    """Creates DICOM file(s) with the data parsed from
    the input file.

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
    output_filename = f"{Path(input_file).stem}.dcm"
    filepath = Path(output_dir, output_filename)
    file = write_opt_dicom(meta, oct.volume, filepath)
    files.append(file)

    # Attempt to parse fundus images
    fundus = fda.read_fundus_image()
    if fundus:
        output_filename = f"{Path(input_file).stem}_fundus.dcm"
        filepath = Path(output_dir, output_filename)
        meta.image_geometry.pixel_spacing = [1, 1]
        file = write_color_fundus_dicom(meta, fundus.image, filepath)
        files.append(file)

    fundus_grayscale = fda.read_fundus_image_gray_scale()
    if fundus_grayscale:
        output_filename = f"{Path(input_file).stem}_fundus_grayscale.dcm"
        filepath = Path(output_dir, output_filename)
        meta.image_geometry.pixel_spacing = [1, 1]
        file = write_fundus_dicom(meta, fundus_grayscale.image, filepath)
        files.append(file)

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
    files.append(file)

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
    return [file]


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
        files.append(file)

    return files
