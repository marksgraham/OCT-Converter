from __future__ import annotations

import re
from datetime import datetime
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
        file_info = {}
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
                if "Eye Scanned" in line:
                    if "OD" in line:
                        file_info["laterality"] = "R"
                    elif "OS" in line:
                        file_info["laterality"] = "L"
                if "Video Height" in line:
                    file_info["video_height"] = line.split("=")[-1]
                if "Video Width" in line:
                    file_info["video_width"] = line.split("=")[-1]
                if "BitCount" in line:
                    file_info["bitcount"] = line.split("=")[-1]
                if "Physical video width" in line:
                    file_info["physical_width"] = line.split("=")[-1]
                if "Physical video Height" in line:
                    file_info["physical_height"] = line.split("=")[-1]

        if "video_height" in file_info and "physical_height" in file_info:
            file_info["scale_y"] = float(file_info["physical_height"].split()[0]) / abs(
                float(file_info["video_height"])
            )
        if "video_width" in file_info and "physical_width" in file_info:
            file_info["scale_x"] = float(file_info["physical_width"].split()[0]) / abs(
                float(file_info["video_width"])
            )

        # Attempt to find acquisition date in filename
        acq = (
            list(
                re.search(
                    r"(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})_(?P<h>\d{1,2}).(?P<M>\d{1,2}).(?P<s>\d{1,2})",
                    str(self.filespec),
                ).groups()
            )
            if re.search(
                r"(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})_(?P<h>\d{1,2}).(?P<M>\d{1,2}).(?P<s>\d{1,2})",
                str(self.filespec),
            )
            else None
        )
        if acq:
            file_info["acquisition_date"] = datetime(
                year=int(acq[0]),
                month=int(acq[1]),
                day=int(acq[2]),
                hour=int(acq[3]),
                minute=int(acq[4]),
                second=int(acq[5]),
            )

        self.scan_info = scan_info
        self.file_info = file_info

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
                all_volumes.append(
                    OCTVolumeWithMetaData(
                        all_slices,
                        acquisition_date=self.file_info.get("acquisition_date", None),
                        laterality=self.file_info.get("laterality", ""),
                        pixel_spacing=[
                            self.file_info.get("scale_x", 0.015),
                            self.file_info.get("scale_y", 0.015),
                        ],
                    )
                )
        return all_volumes
