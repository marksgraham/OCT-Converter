import numpy as np
from oct_converter.image_types import OCTVolumeWithMetaData, FundusImageWithMetaData


class IMG(object):
    """ Class for extracting data from Zeiss's .img file format.

        Attributes:
            filepath (str): Path to .img file for reading.
    """

    def __init__(self, filepath):
        self.filepath = filepath

    def read_oct_volume(self):
        """ Reads OCT data.

            Returns:
                obj:OCTVolumeWithMetaData
        """
        with open(self.filepath, 'rb') as f:
            volume = np.fromstring(f.read(), dtype=np.uint8)
            volume = volume.reshape((1024, 512, 128), order='F')
            shape = volume.shape
            # volume = np.transpose(volume, [2, 1, 0])

            interlaced = np.zeros((int(shape[0] / 2), shape[1], shape[2] * 2))
            interlaced[..., 0::2] = volume[:512, ...]
            interlaced[..., 1::2] = volume[512:, ...]
            interlaced = np.rot90(interlaced, axes=(0, 1))
        oct_volume = OCTVolumeWithMetaData([interlaced[:, :, i] for i in range(interlaced.shape[2])])
        return oct_volume
