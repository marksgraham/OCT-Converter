"""With many, many thanks to scaramallion, https://github.com/pydicom/pydicom/discussions/1618"""
import math

from pydicom import dcmread
from pydicom.dataelem import validate_value, DataElement
from pydicom.dataset import validate_file_meta
from pydicom.encaps import generate_pixel_data_frame, encapsulate
from pydicom.uid import JPEG2000Lossless, ExplicitVRLittleEndian


def unscramble_czm(frame: bytes) -> bytearray:
    """Return an unscrambled image frame.

    Parameters
    ----------
    frame : bytes
        The scrambled CZM JPEG 2000 data frame as found in the DICOM dataset.

    Returns
    -------
    bytearray
        The unscrambled JPEG 2000 data.
    """
    # Fix the 0x5A XORing
    frame = bytearray(frame)
    for ii in range(0, len(frame), 7):
        frame[ii] = frame[ii] ^ 0x5A

    # Offset to the start of the JP2 header - empirically determined
    jp2_offset = math.floor(len(frame) / 5 * 3)

    # Double check that our empirically determined jp2_offset is correct
    offset = frame.find(b"\x00\x00\x00\x0C")
    if offset == -1:
        raise ValueError("No JP2 header found in the scrambled pixel data")

    if jp2_offset != offset:
        print(
            f"JP2 header found at offset {offset} rather than the expected "
            f"{jp2_offset}"
        )
        jp2_offset = offset

    d = bytearray()
    d.extend(frame[jp2_offset:jp2_offset + 253])
    d.extend(frame[993:1016])
    d.extend(frame[276:763])
    d.extend(frame[23:276])
    d.extend(frame[1016:jp2_offset])
    d.extend(frame[:23])
    d.extend(frame[763:993])
    d.extend(frame[jp2_offset + 253:])

    assert len(d) == len(frame)

    return d


def tag_fixer(element: DataElement) -> DataElement:
    """Given a DataElement, attempts to remove the basic
    obfuscation added to various tags. If element is valid,
    returns element. If element is invalid, empties value
    and returns element.
    
    Args:
        element: DICOM tag data as DataElement
    
    Returns:
        DataElement with more-conformant values
    """
    try:
        element.value = element.value.split("\x00")[0]
    except:
        pass
    try:
        validate_value(element.VR, element.value, validation_mode=2)
        return element
    except ValueError:
        element.value = ""
        return element


def process_file(input_file: str, output_filename: str) -> None:
    """Utilizes Pydicom to read the dataset, check that the
    dataset is CZM, applies fixers, and outputs a deobfuscated
    DICOM.

    Args:
        input_file: Path to input file as a string
        output_filename: Name under which to save the DICOM
    """
    # Read and check the dataset is CZM
    ds = dcmread(input_file)
    meta = ds.file_meta
    if meta.TransferSyntaxUID != JPEG2000Lossless:
        raise ValueError(
            "Only DICOM datasets with a 'Transfer Syntax UID' of JPEG 2000 "
            "(Lossless) are supported"
        )

    if not ds.Manufacturer.startswith("Carl Zeiss Meditec"):
        raise ValueError("Only CZM DICOM datasets are supported")

    if "PixelData" not in ds:
        raise ValueError("No 'Pixel Data' found in the DICOM dataset")
    
    # Specific tag fixers
    ds.PixelSpacing = ds.PixelSpacing.split("\x00")[0].split(",")
    ds.OperatorsName = ds.OperatorsName.original_string.split(b"\x00")[0].decode()
    ds.PatientName = ds.PatientName.original_string.split(b"=")[0].decode()
    ds.Modality = "OPT"
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]

    lat_map = {"OD": "R", "OS": "L", "": "", None: ""}
    ds.Laterality = lat_map.get(ds.Laterality, None)

    # Clean obfuscated tags
    for element in ds:
        if element.VR not in ["SQ", "OB"]:
            tag_fixer(element)
        elif element.VR == "SQ":
            for sequence in element:
                for e in sequence:
                    tag_fixer(e)
    for element in meta:
        tag_fixer(element)

    # Make sure file_meta is conformant
    validate_file_meta(meta, enforce_standard=True)

    # Iterate through the frames, unscramble and write to file
    if "NumberOfFrames" in ds:
        all_frames = []
        frames = generate_pixel_data_frame(ds.PixelData, int(ds.NumberOfFrames))
        for idx, frame in enumerate(frames):
            all_frames.append(unscramble_czm(frame))
        ds.PixelData = encapsulate(all_frames)
    else:
        frame = unscramble_czm(ds.PixelData)
        ds.PixelData = encapsulate([frame])

    # And finally, convert pixel data to ExplicitVRLittleEndian
    ds.decompress()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.is_implicit_VR = False
    ds.is_little_endian = True
    
    ds.save_as(output_filename)
