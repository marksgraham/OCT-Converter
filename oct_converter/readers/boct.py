from __future__ import annotations

import tempfile
from pathlib import Path
from typing import BinaryIO, List, Tuple, Union

import h5py
import numpy as np
from construct import Struct
from numpy.typing import NDArray

from oct_converter.exceptions import InvalidOCTReaderError
from oct_converter.image_types import OCTVolumeWithMetaData
from oct_converter.readers.binary_structs import boct_binary


class BOCT(object):
    """Class for extracting data from Bioptigen's .OCT file format.
    .OCT stores 4d volumes (time series of 3D volumes with the same shape)

    Attributes:
        filepath (str): Path to .img file for reading.
        file_structure (obj:Struct): Defines structure of volume's header.
    """

    bioptigen_scan_type_map = {0: "linear", 1: "rect", 3: "rad"}
    file_structure = boct_binary.bioptigen_file_structure
    header_structure = boct_binary.bioptigen_oct_header_struct

    def __init__(self, filepath: Union[Path, str]):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)
        self._validate(self.filepath)

    def _validate(self, path: Path) -> bool:
        try:
            self.header_structure.parse_file(path)
        except UnicodeDecodeError:
            raise InvalidOCTReaderError(
                "OCT header does not match Bioptigen .OCT format. Did you mean to use Optovue .oct (POCT)?"
            )
        return True

    def read_oct_volume(
        self, diskbuffered: bool = False
    ) -> List[OCTVolumeWithMetaData]:
        """Reads OCT data.
        Args:
            diskbuffered (bool): If True, reduces memory usage by storing volume on disk using HDF5

        Returns:
            list(obj):[OCTVolumeWithMetaData]
        """
        # Laterality/patient_id data not contained in .OCT file (often in filename)
        self.laterality = None
        self.patient_id = self.filepath.stem

        # Lazily parse the file without loading frame pixels
        oct = self.file_structure.parse_file(self.filepath)
        header = oct.header
        self.frames = FrameGenerator(oct.data)
        scantype = self.bioptigen_scan_type_map[header.scantype.value]
        framecount = header.frames.value
        scancount = header.scans.value
        if scantype == "linear":
            # linear bscans can contain multiple scans at one position
            # reorder into (framecount*scancount,1,y,x)
            framecount *= scancount
            scancount = 1

        self.volume_shape = (
            framecount,
            scancount,
            self.frames.Ascans,
            self.frames.depth,
        )
        bscan_shape = (self.volume_shape[2], self.volume_shape[3])
        self.vol_frames_shape = (self.volume_shape[0], self.volume_shape[1])
        if diskbuffered:
            self.vol = self._create_disk_buffer(buffer_shape=bscan_shape)
        else:
            self.vol = np.empty(self.volume_shape, dtype=np.uint16)

        return self.load_oct_volume()

    def _create_disk_buffer(
        self, buffer_shape: Tuple[int, int], name: str = "vol"
    ) -> h5py.Dataset:
        x, y = buffer_shape
        chunksize = (1, 1, x, y)
        tf = h5py.File(tempfile.TemporaryFile(), "w")
        return tf.create_dataset(
            name, shape=self.volume_shape, dtype=np.uint16, chunks=chunksize
        )

    def load_oct_volume(self) -> List[OCTVolumeWithMetaData]:
        volFrames = np.reshape(self.frames.data, self.vol_frames_shape)
        try:
            with open(self.filepath, "rb") as f:
                for t, v in enumerate(volFrames):
                    for z, frame in enumerate(v):
                        self.vol[t, z, :, :] = frame.load(
                            f, self.frames.Ascans, self.frames.depth
                        )
        except Exception as e:
            print(e)
            print("Stopping load")
        return [
            OCTVolumeWithMetaData(self.vol[t, :, :, :])
            for t in range(self.vol.shape[0])
        ]

    def read_fundus_image(self) -> None:
        return


class OCTFrame:
    def __init__(self, frame: Struct):
        self.count = frame.image.totalpixels
        self.abs_pos = frame.image.offset

    def from_bytes(self, f: BinaryIO) -> NDArray[np.uint16]:
        f.seek(self.abs_pos, 0)
        im = np.fromfile(f, dtype=np.uint16, count=self.count)
        return im

    def load(self, f: BinaryIO, Ascans: int, depth: int) -> NDArray[np.uint16]:
        return np.resize(self.from_bytes(f), (Ascans, depth))


class FrameGenerator:
    def __init__(self, oct_data: Struct):
        self.Ascans = oct_data[0].image.columns
        self.depth = oct_data[0].image.rows
        self.data = np.asarray([OCTFrame(frame) for frame in oct_data])
        self.count = len(self.data)

    def reorder(self, indexArr: NDArray[np.int_]) -> FrameGenerator:
        try:
            self.data = self.data[indexArr]
        except Exception as e:
            print(e)
        finally:
            return self
