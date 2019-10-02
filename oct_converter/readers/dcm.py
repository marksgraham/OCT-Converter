from oct_converter.image_types import OCTVolumeWithMetaData, FundusImageWithMetaData


class Dicom(object):
    def __init__(self, filepath):
        self.filepath = filepath

    def read_oct_volume(self):
        """ Reads OCT data.

            Returns:
                obj:OCTVolumeWithMetaData
        """
        import pydicom
        dicom_data = pydicom.dcmread(self.filepath)
        pixel_data = dicom_data.pixel_array
        oct_volume = OCTVolumeWithMetaData(volume=pixel_data)
        return oct_volume
