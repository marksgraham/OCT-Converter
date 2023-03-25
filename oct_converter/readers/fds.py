from pathlib import Path

import numpy as np

from oct_converter.image_types import FundusImageWithMetaData, OCTVolumeWithMetaData
from oct_converter.readers.binary_structs import fds_binary


class FDS(object):
    """Class for extracting data from Topcon's .fds file format.

    Notes:
        Mostly based on description of .fds file format here:
        https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format

    Attributes:
        filepath (str): Path to .img file for reading.
        chunk_dict (dict): Name of data chunks present in the file, and their start locations.
    """

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)

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
            header = fds_binary.header.parse(raw)

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
        if b"@IMG_SCAN_03" not in self.chunk_dict:
            raise ValueError("Could not find OCT header @IMG_SCAN_03 in chunk list")
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@IMG_SCAN_03"]
            f.seek(chunk_location)
            raw = f.read(22)
            oct_header = fds_binary.oct_header.parse(raw)
            number_pixels = (
                oct_header.width * oct_header.height * oct_header.number_slices
            )
            raw_volume = np.fromstring(f.read(number_pixels * 2), dtype=np.uint16)
            volume = np.array(raw_volume)
            volume = volume.reshape(
                oct_header.width, oct_header.height, oct_header.number_slices, order="F"
            )
            volume = np.transpose(volume, [1, 0, 2])
            chunk_loc, chunk_size = self.chunk_dict.get(b"@PARAM_SCAN_04", (None, None))
            pixel_spacing = None
            if chunk_loc:
                f.seek(chunk_loc)
                scan_params = fds_binary.param_scan_04_header.parse(f.read(chunk_size))
                # NOTE: this will need reordering for dicom pixel spacing and
                # image orientation/position patient as well as possibly for nifti
                # depending on what x,y,z means here.

                # In either nifti/dicom coordinate systems, the x-y plan in raw space
                # corresponds to the x-z plane, just depends which direction.
                pixel_spacing = [
                    scan_params.x_dimension_mm / oct_header.height,  # Left/Right
                    scan_params.z_resolution_um / 1000,  # Up/Down
                    scan_params.y_dimension_mm / oct_header.width,  # Depth
                ]

        oct_volume = OCTVolumeWithMetaData(
            [volume[:, :, i] for i in range(volume.shape[2])],
            pixel_spacing=pixel_spacing,
        )
        return oct_volume

    def read_fundus_image(self):
        """Reads fundus image.

        Returns:
            obj:FundusImageWithMetaData
        """
        if b"@IMG_OBS" not in self.chunk_dict:
            raise ValueError("Could not find fundus header @IMG_OBS in chunk list")
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@IMG_OBS"]
            f.seek(chunk_location)
            raw = f.read(21)
            fundus_header = fds_binary.fundus_header.parse(raw)
            # number_pixels = fundus_header.width * fundus_header.height * fundus_header.number_slices
            raw_image = np.fromstring(f.read(fundus_header.size), dtype=np.uint8)
            # raw_image = [struct.unpack('B', f.read(1)) for pixel in range(fundus_header.size)]
            image = np.array(raw_image)
            image = image.reshape(
                3, fundus_header.width, fundus_header.height, order="F"
            )
            image = np.transpose(image, [2, 1, 0])
            image = image.astype(np.float32)
        fundus_image = FundusImageWithMetaData(image)
        return fundus_image
