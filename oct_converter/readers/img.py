import numpy as np
from oct_converter.image_types import OCTVolumeWithMetaData, FundusImageWithMetaData
from pathlib import Path

class IMG(object):
    """ Class for extracting data from Zeiss's .img file format.

        Attributes:
            filepath (str): Path to .img file for reading.
    """

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)

    def read_oct_volume(self):
        """ Reads OCT data.

            Returns:
                obj:OCTVolumeWithMetaData
        """
        with open(self.filepath, 'rb') as f:
            volume = np.frombuffer(f.read(), dtype=np.uint8)  # np.fromstring() gives numpy depreciation warning
            num_slices = len(volume) // (1024*512)
            volume = volume.reshape((1024, 512, num_slices), order='F')   
            shape = volume.shape

            interlaced = np.zeros((int(shape[0] / 2), shape[1], shape[2] * 2))
            interlaced[..., 0::2] = volume[:512, ...]
            interlaced[..., 1::2] = volume[512:, ...]
            interlaced = np.rot90(interlaced, axes=(0, 1))
        oct_volume = OCTVolumeWithMetaData([interlaced[:, :, i] for i in range(interlaced.shape[2])])
        return oct_volume
