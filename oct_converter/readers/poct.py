from __future__ import annotations

from pathlib import Path

import numpy as np

from oct_converter.image_types import OCTVolumeWithMetaData


class POCT(object):
    """Class for extracting data from Optovues's .oct file format.

    Attributes:
        filepath: path to .oct file for reading. Expects a file with the same name and a .txt extension
            exists at the same location.
    """

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)
        self.filespec = self.filepath.with_suffix(".txt")
        if not self.filespec.exists():
            raise FileNotFoundError(
                f"Could not find filespec {self.filespec} in the same location as {self.filepath}"
            )

    def _read_filespec(self) -> None:
        scan_info = []
        with open(self.filespec, "r", encoding="iso-8859-1") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if "Window Height" in line:
                    height = [int(s) for s in line.split() if s.isdigit()][0]
                if "Scan Length" in line and "Scan Usage" in lines[i + 1]:
                    scan_length = [int(s) for s in line.split() if s.isdigit()][0]
                    scan_number = [int(s) for s in lines[i + 1].split() if s.isdigit()][
                        0
                    ]
                    scan_info.append(
                        {"height": height, "length": scan_length, "number": scan_number}
                    )
        self.scan_info = scan_info

    def read_oct_volume(self) -> list[OCTVolumeWithMetaData]:
        """Reads OCT data.

        Returns:
            OCTVolumeWithMetaData
        """
        self._read_filespec()

        with open(self.filepath, "rb") as f:
            data = np.frombuffer(
                f.read(), dtype=np.float32
            )  # np.fromstring() gives numpy depreciation warning
            all_volumes = []
            for volume in self.scan_info:
                num_pixels_slice = volume["height"] * volume["length"]
                num_slices = volume["number"]
                all_slices = []
                for i in range(num_slices):
                    slice = data[i * num_pixels_slice : (i + 1) * num_pixels_slice]
                    slice = np.rot90(slice.reshape(volume["length"], volume["height"]))
                    all_slices.append(slice)
                all_volumes.append(OCTVolumeWithMetaData(all_slices))
        return all_volumes
