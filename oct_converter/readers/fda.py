from pathlib import Path

import numpy as np
from construct import Int32un, PaddedString, Struct
from pylibjpeg import decode

from oct_converter.image_types import FundusImageWithMetaData, OCTVolumeWithMetaData


class FDA(object):
    """Class for extracting data from Topcon's .fda file format.

    Notes:
        Mostly based on description of .fda file format here:
        https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format

    Attributes:
        filepath (str): Path to .img file for reading.
        header (obj:Struct): Defines structure of volume's header.
        oct_header (obj:Struct): Defines structure of OCT header.
        fundus_header (obj:Struct): Defines structure of fundus header.
        chunk_dict (dict): Name of data chunks present in the file, and their start locations.
    """

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)
        self.header = Struct(
            "FOCT" / PaddedString(4, "ascii"),
            "FDA" / PaddedString(3, "ascii"),
            "version_info_1" / Int32un,
            "version_info_2" / Int32un,
        )
        self.oct_header = Struct(
            "type" / PaddedString(1, "ascii"),
            "unknown1" / Int32un,
            "unknown2" / Int32un,
            "width" / Int32un,
            "height" / Int32un,
            "number_slices" / Int32un,
            "unknown3" / Int32un,
        )

        self.oct_header_2 = Struct(
            "unknown" / PaddedString(1, "ascii"),
            "width" / Int32un,
            "height" / Int32un,
            "bits_per_pixel" / Int32un,
            "number_slices" / Int32un,
            "unknown" / PaddedString(1, "ascii"),
            "size" / Int32un,
        )

        self.fundus_header = Struct(
            "width" / Int32un,
            "height" / Int32un,
            "bits_per_pixel" / Int32un,
            "number_slices" / Int32un,
            "unknown" / PaddedString(4, "ascii"),
            "size" / Int32un,
            # 'img' / Int8un,
        )

        self.chunk_dict = self.get_list_of_file_chunks()

    def get_list_of_file_chunks(self):
        """Find all data chunks present in the file.

        Returns:
            dict
        """
        chunk_dict = {}
        with open(self.filepath, "rb") as f:
            # skip header
            raw = f.read(15)
            header = self.header.parse(raw)

            eof = False
            while not eof:
                chunk_name_size = np.fromstring(f.read(1), dtype=np.uint8)[0]
                if chunk_name_size == 0:
                    eof = True
                else:
                    chunk_name = f.read(chunk_name_size)
                    chunk_size = np.fromstring(f.read(4), dtype=np.uint32)[0]
                    chunk_location = f.tell()
                    f.seek(chunk_size, 1)
                    chunk_dict[chunk_name] = [chunk_location, chunk_size]
        print("File {} contains the following chunks:".format(self.filepath))
        for key in chunk_dict.keys():
            print(key)
        return chunk_dict

    def read_oct_volume(self):
        """Reads OCT data.

        Returns:
            obj:OCTVolumeWithMetaData
        """

        if b"@IMG_JPEG" not in self.chunk_dict:
            raise ValueError("Could not find OCT header @IMG_JPEG in chunk list")
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@IMG_JPEG"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read(25)
            oct_header = self.oct_header.parse(raw)
            volume = np.zeros(
                (oct_header.height, oct_header.width, oct_header.number_slices)
            )
            for i in range(oct_header.number_slices):
                size = np.fromstring(f.read(4), dtype=np.int32)[0]
                raw_slice = f.read(size)
                slice = decode(raw_slice)
                volume[:, :, i] = slice
        oct_volume = OCTVolumeWithMetaData(
            [volume[:, :, i] for i in range(volume.shape[2])]
        )
        return oct_volume

    def read_oct_volume_2(self):
        """Reads OCT data.

        Returns:
            obj:OCTVolumeWithMetaData
        """

        if b"@IMG_MOT_COMP_03" not in self.chunk_dict:
            raise ValueError("Could not find OCT header @IMG_MOT_COMP_03 in chunk list")
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@IMG_MOT_COMP_03"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read(22)
            oct_header = self.oct_header_2.parse(raw)
            number_pixels = (
                oct_header.width * oct_header.height * oct_header.number_slices
            )
            raw_volume = np.fromstring(f.read(number_pixels * 2), dtype=np.uint16)
            volume = np.array(raw_volume)
            volume = volume.reshape(
                oct_header.width, oct_header.height, oct_header.number_slices, order="F"
            )
            volume = np.transpose(volume, [1, 0, 2])
        oct_volume = OCTVolumeWithMetaData(
            [volume[:, :, i] for i in range(volume.shape[2])]
        )
        return oct_volume

    def read_fundus_image(self):
        """Reads fundus image.

        Returns:
            obj:FundusImageWithMetaData
        """
        if b"@IMG_FUNDUS" not in self.chunk_dict:
            raise ValueError("Could not find fundus header @IMG_FUNDUS in chunk list")
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@IMG_FUNDUS"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read(24)  # skip 24 is important
            fundus_header = self.fundus_header.parse(raw)
            number_pixels = fundus_header.width * fundus_header.height * 3
            raw_image = f.read(fundus_header.size)
            image = decode(raw_image)
        fundus_image = FundusImageWithMetaData(image)
        return fundus_image
