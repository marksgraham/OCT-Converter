from pathlib import Path

from oct_converter.image_types import OCTVolumeWithMetaData


class Dicom(object):
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)

    def read_oct_volume(self):
        """Reads OCT data.

        Returns:
            obj:OCTVolumeWithMetaData
        """
        import pydicom

        dicom_data = pydicom.dcmread(self.filepath)
        if dicom_data.Manufacturer.startswith("Carl Zeiss Meditec"):
            raise ValueError(
                "This appears to be a Zeiss DCM. You may need to read with the ZEISSDCM class."
            )
        pixel_data = dicom_data.pixel_array
        oct_volume = OCTVolumeWithMetaData(volume=pixel_data)
        return oct_volume
