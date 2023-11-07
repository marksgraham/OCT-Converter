from __future__ import annotations

import re
from datetime import datetime
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

        meta = self.get_metadata_from_filename()
        lat_map = {"OD": "R", "OS": "L", None: ""}

        oct_volume = OCTVolumeWithMetaData(
            [volume[:, :, i] for i in range(volume.shape[2])],
            patient_id=meta.get("patient_id"),
            acquisition_date=meta.get("acquisition_date"),
            laterality=lat_map[meta.get("laterality", None)],
            metadata=meta,
        )
        return oct_volume

    def get_metadata_from_filename(self) -> dict:
        """Attempts to find metadata within the filename

        Returns:
            meta: dict of information extracted from filename
        """
        filename = Path(self.filepath).name
        meta = {}
        meta["patient_id"] = (
            re.search(r"^P\d+", filename).group(0)
            if re.search(r"^P\d+", filename)
            else None
        )
        acq = (
            list(
                re.search(
                    r"(?P<m>\d{1,2})-(?P<d>\d{1,2})-(?P<y>\d{4})_(?P<h>\d{1,2})-(?P<M>\d{1,2})-(?P<s>\d{1,2})",
                    filename,
                ).groups()
            )
            if re.search(
                r"(?P<m>\d{1,2})-(?P<d>\d{1,2})-(?P<y>\d{4})_(?P<h>\d{1,2})-(?P<M>\d{1,2})-(?P<s>\d{1,2})",
                filename,
            )
            else None
        )
        if acq:
            meta["acquisition_date"] = datetime(
                year=int(acq[2]),
                month=int(acq[0]),
                day=int(acq[1]),
                hour=int(acq[3]),
                minute=int(acq[4]),
                second=int(acq[5]),
            )
        meta["laterality"] = (
            re.search(r"O[D|S]", filename).group(0)
            if re.search(r"O[D|S]", filename)
            else None
        )
        meta["sn"] = (
            re.search(r"sn\d+", filename).group(0)
            if re.search(r"sn\d*", filename)
            else None
        )

        return meta
