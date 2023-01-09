from pathlib import Path

import numpy as np

from oct_converter.image_types import OCTVolumeWithMetaData


class IMG(object):
    """Class for extracting data from Zeiss's .img file format.

    Attributes:
        filepath (str): Path to .img file for reading.
    """

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)

    def read_oct_volume(self, rows=1024, cols=512, interlaced=False):
        """Reads OCT data.
        Args:
            interlaced (bool): Determines whether data needs to be de-interlaced.

            Returns:
                obj:OCTVolumeWithMetaData
        """
        with open(self.filepath, "rb") as f:
            volume = np.frombuffer(
                f.read(), dtype=np.uint8
            )  # np.fromstring() gives numpy depreciation warning
            num_slices = len(volume) // (rows * cols)
            volume = volume.reshape((rows, cols, num_slices), order="F")
            if interlaced:
                shape = volume.shape
                interlaced = np.zeros((int(shape[0] / 2), shape[1], shape[2] * 2))
                interlaced[..., 0::2] = volume[:cols, ...]
                interlaced[..., 1::2] = volume[cols:, ...]
                interlaced = np.rot90(interlaced, axes=(0, 1))
                volume = interlaced

        oct_volume = OCTVolumeWithMetaData(
            [volume[:, :, i] for i in range(volume.shape[2])]
        )
        return oct_volume, num_slices
