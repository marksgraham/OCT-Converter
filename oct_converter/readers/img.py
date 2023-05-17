from __future__ import annotations

from pathlib import Path

import numpy as np

from oct_converter.image_types import OCTVolumeWithMetaData


class IMG(object):
    """Class for extracting data from Zeiss's .img file format.

    Attributes:
        filepath: path to .img file for reading.
    """

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)

    def read_oct_volume(
        self, rows: int = 1024, cols: int = 512, interlaced: bool = False
    ):
        """Reads OCT data.

        Args:
            rows: can be used to specify a custom row dimension of the image slice. Defaults to 1024 pixels.
            cols: dan be used to specify a custom column dimension of the image slice. Defaults to 512 pixels.
            interlaced: determines whether data needs to be de-interlaced.

        Returns:
            OCTVolumeWithMetaData
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
        return oct_volume
