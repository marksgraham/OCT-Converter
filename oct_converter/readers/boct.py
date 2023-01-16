import tempfile
from pathlib import Path

import h5py
import numpy as np
from construct import (
    Array,
    Bytes,
    BytesInteger,
    Computed,
    Float64n,
    Hex,
    Int16un,
    Int32un,
    Lazy,
    PaddedString,
    Seek,
    Struct,
    Tell,
    this,
)

from oct_converter.image_types import OCTVolumeWithMetaData

headerField = Struct(
    keylength=Int32un, key=PaddedString(this.keylength, "utf8"), dataLength=Int32un
)

floatField = Struct(
    keylength=Int32un,
    key=PaddedString(this.keylength, "utf8"),
    dataLength=Int32un,
    value=Float64n,
)

intField = Struct(
    keylength=Int32un,
    key=PaddedString(this.keylength, "utf8"),
    dataLength=Int32un,
    value=BytesInteger(this.dataLength, signed=False, swapped=True),
)

lazyIntField = Struct(
    "keylength" / Int32un,
    "key" / PaddedString(this.keylength, "utf8"),
    "dataLength" / Int32un,
    "offset" / Tell,
    "end" / Computed(this.offset + this.dataLength),
    "value" / Lazy(Bytes(this.dataLength)),
    Seek(this.end),
)

date = Struct(
    year=Int16un,
    month=Int16un,
    dow=Int16un,
    day=Int16un,
    hour=Int16un,
    minute=Int16un,
    second=Int16un,
    millisecond=Int16un,
)
dateField = Struct(
    keylength=Int32un,
    key=PaddedString(this.keylength, "utf8"),
    dataLength=Int32un,
    value=date,
)

strField = Struct(
    keylength=Int32un,
    key=PaddedString(this.keylength, "utf8"),
    dataLength=Int32un,
    value=PaddedString(this.dataLength, "utf8"),
)


class BOCT(object):
    """Class for extracting data from Bioptigen's .OCT file format.
    .OCT stores 4d volumes (time series of 3D volumes with the same shape)

    Attributes:
        filepath (str): Path to .img file for reading.
        header_structure (obj:Struct): Defines structure of volume's header.
        main_directory_structure (obj:Struct): Defines structure of volume's main directory.
        sub_directory_structure (obj:Struct): Defines structure of each sub directory in the volume.
        chunk_structure (obj:Struct): Defines structure of each data chunk.
        image_structure (obj:Struct): Defines structure of image header.
    """

    bioptigen_scan_type_map = {0: "linear", 1: "rect", 3: "rad"}

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)

        self.oct_header = Struct(
            "magicNumber" / Hex(Int32un),
            "version" / Hex(Int16un),
            "frameheader" / headerField,
            "framecount" / intField,
            "linecount" / intField,
            "linelength" / intField,
            "sampleformat" / intField,
            "description" / strField,
            "xmin" / floatField,
            "xmax" / floatField,
            "xcaption" / strField,
            "ymin" / floatField,
            "ymax" / floatField,
            "ycaption" / strField,
            "scantype" / intField,
            "scandepth" / floatField,
            "scanlength" / floatField,
            "azscanlength" / floatField,
            "elscanlength" / floatField,
            "objectdistance" / floatField,
            "scanangle" / floatField,
            "scans" / intField,
            "frames" / intField,
            "dopplerflag" / intField,
            "config" / lazyIntField,
            BytesInteger(4, signed=False, swapped=True),
        )
        self.frame_header = Struct(
            "framedata" / headerField,
            "framedatetime" / dateField,
            "frametimestamp" / floatField,
            "framelines" / intField,
            "keylength" / Int32un,
            "key" / PaddedString(this.keylength, "utf8"),
            "dataLength" / Int32un,
        )

        self.frame_image = Struct(
            "rows" / Computed(this._._.header.linelength.value),
            "columns" / Computed(this._.header.framelines.value),
            "totalpixels" / Computed(this.rows * this.columns),
            "offset" / Tell,
            "end" / Computed(this.offset + this.totalpixels * 2),
            "pixels" / Lazy(Array(this.totalpixels, Int16un)),
            Seek(this.end),
        )

        self.frame = Struct(
            "header" / self.frame_header,
            "image" / self.frame_image,
            BytesInteger(4, signed=False, swapped=True),
        )

        self.frame_stack = Array(this.header.framecount.value, self.frame)
        self.file_structure = Struct(
            "header" / self.oct_header, "data" / self.frame_stack
        )

    def read_oct_volume(self, diskbuffered=False):
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
        self.vol_frames_shape = (self.volume_shape[0], self.volume_shape[1])

        # Index conversion between 3D framestack (z+t,y,x) and 4D volume (t,z,x,y)
        stack_to_vol = np.asarray(
            [
                i + j * (framecount)
                for i in range(0, framecount)
                for j in range(0, scancount)
            ]
        )
        vol_to_stack = np.asarray(
            [
                i + j * (scancount)
                for i in range(0, scancount)
                for j in range(0, framecount)
            ]
        )
        self.indicies = {"to_vol": stack_to_vol, "to_stack": vol_to_stack}
        self._loaded = False
        if diskbuffered:
            self._create_disk_buffer()
        else:
            self.vol = np.empty(self.volume_shape, dtype=np.uint16)

        return self.load_oct_volume()

    def _create_disk_buffer(self, name="vol"):
        _, _, x, y = self.volume_shape
        chunksize = (1, 1, x, y)
        tf = h5py.File(tempfile.TemporaryFile(), "w")
        buffer = tf.create_dataset(
            name, shape=self.volume_shape, dtype=np.uint16, chunks=chunksize
        )
        setattr(self, name, buffer)

    def load_oct_volume(self):
        volFrames = np.reshape(self.frames.data, self.vol_frames_shape)
        try:
            with open(self.filepath, "rb") as f:
                for t, v in enumerate(volFrames):
                    for z, frame in enumerate(v):
                        self.vol[t, z, :, :] = frame.load(f, self.frames.geom)
            self.loaded = True
        except Exception as e:
            print(e)
            print("Stopping load")
        return [
            OCTVolumeWithMetaData(self.vol[t, :, :, :])
            for t in range(self.vol.shape[0])
        ]

    def read_fundus_image(self):
        pass


class OCTFrame:
    def __init__(self, frame):
        self.frame = frame
        self.count = self.frame.image.totalpixels
        self.abs_pos = self.frame.image.offset

    def from_bytes(self, f):
        f.seek(self.abs_pos, 0)
        im = np.fromfile(f, dtype=np.uint16, count=self.count)
        return im

    def load(self, f, imsize):
        return np.resize(self.from_bytes(f), imsize)

    def __eq__(self, other):
        return self.im == other


class FrameGenerator:
    def __init__(self, oct_data):
        self.data = None
        self.oct_data = oct_data

        frame0 = oct_data[0]
        self.Ascans = frame0.image.columns
        self.depth = frame0.image.rows
        self.geom = (self.Ascans, self.depth)
        self.data = np.asarray([OCTFrame(frame) for frame in self.oct_data])
        self.count = len(self.data)

    def set_frameorder(self, indexArr):
        try:
            self.data = self.data[indexArr]
        except Exception as e:
            print(e)
