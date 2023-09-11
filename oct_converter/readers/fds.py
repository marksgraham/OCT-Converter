from __future__ import annotations

import typing as t
from datetime import datetime
from pathlib import Path

import numpy as np
from construct import ListContainer

from oct_converter.image_types import FundusImageWithMetaData, OCTVolumeWithMetaData
from oct_converter.readers.binary_structs import fds_binary


class FDS(object):
    """Class for extracting data from Topcon's .fds file format.

    Notes:
        Mostly based on description of .fds file format here:
        https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format

    Attributes:
        filepath: path to .img file for reading.
        chunk_dict: names of data chunks present in the file, and their start locations.
    """

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)

        self.chunk_dict, self.header = self.get_list_of_file_chunks()

    def get_list_of_file_chunks(self, printing: bool = False) -> t.Tuple[dict, dict]:
        """Find all data chunks present in the file.

        Returns:
            chunk_dict: dictionary of chunk names, containing their locations
            in the file and size.
            header: dictionary of file header information

        """
        chunk_dict = {}
        with open(self.filepath, "rb") as f:
            raw = f.read(15)
            header = dict(fds_binary.header.parse(raw))

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
        if printing:
            print("File {} contains the following chunks:".format(self.filepath))
            for key in chunk_dict.keys():
                print(key)
            print("")
        return chunk_dict, header

    def read_oct_volume(self) -> OCTVolumeWithMetaData:
        """Reads OCT data.

        Returns:
            OCTVolumeWithMetaData
        """
        # TODO: could support the other IMG_SCAN variants as well.
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

        # calculate pixel spacing
        pixel_spacing = self.read_scan_params(oct_header)

        # read all other metadata
        metadata = self.read_all_metadata()
        patient_info = metadata.get("patient_info_02") or metadata.get(
            "patient_info", {}
        )
        capture_info = metadata.get("capture_info_02") or metadata.get(
            "capture_info", {}
        )
        sex_map = {1: "M", 2: "F", 3: "O", None: ""}
        lat_map = {0: "R", 1: "L", None: ""}

        try:
            patient_dob = datetime(*patient_info.get("birth_date"))
        except (TypeError, ValueError):
            patient_dob = None

        oct_volume = OCTVolumeWithMetaData(
            [volume[:, :, i] for i in range(volume.shape[2])],
            patient_id=patient_info.get("patient_id"),
            first_name=patient_info.get("first_name"),
            surname=patient_info.get("last_name"),
            sex=sex_map[patient_info.get("sex", None)],
            patient_dob=patient_dob,
            acquisition_date=datetime(*capture_info.get("cap_date")),
            laterality=lat_map[capture_info.get("eye", None)],
            pixel_spacing=pixel_spacing,
            metadata=metadata,
            header=self.header,
            oct_header=dict(oct_header),
        )
        return oct_volume

    def read_fundus_image(self) -> FundusImageWithMetaData:
        """Reads fundus image.

        Returns:
            FundusImageWithMetaData
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
            # store with RGB channel order
            image = np.flip(image, 2)
        fundus_image = FundusImageWithMetaData(image)
        return fundus_image

    def read_scan_params(self, oct_header: dict) -> list:
        """Given available chunks, identifies available PARAM_SCAN chunk
        and calculates pixel spacing.

        Args:
            oct_header: OCT header information as dict

        Returns:
            pixel_spacing: list of pixel spacing, ordered by width, slice thickness, height.
        """
        if (
            b"@PARAM_SCAN_04" not in self.chunk_dict
            and b"@PARAM_SCAN_02" not in self.chunk_dict
        ):
            print(
                "Neither @PARAM_SCAN_04 nor @PARAM_SCAN_02 found. Pixel spacing not calculated."
            )
            return None
        with open(self.filepath, "rb") as f:
            if b"@PARAM_SCAN_04" in self.chunk_dict:
                chunk_loc, chunk_size = self.chunk_dict.get(
                    b"@PARAM_SCAN_04", (None, None)
                )
                f.seek(chunk_loc)
                scan_params = fds_binary.param_scan_04_header.parse(f.read(chunk_size))
            elif b"@PARAM_SCAN_02" in self.chunk_dict:
                chunk_loc, chunk_size = self.chunk_dict.get(
                    b"@PARAM_SCAN_02", (None, None)
                )
                f.seek(chunk_loc)
                scan_params = fds_binary.param_scan_02_header.parse(f.read(chunk_size))
            pixel_spacing = [
                scan_params.get("x_dimension_mm")
                / oct_header.get("width"),  # WidthPixelS, PixelSpacing[1]
                scan_params.get("y_dimension_mm")
                / oct_header.get("number_slices"),  # FramePixelS / SliceThickness
                scan_params.get("z_resolution_um")
                / 1000,  # zHeightPixelS, PixelSpacing[0]
            ]
        return pixel_spacing

    def read_all_metadata(self, verbose: bool = False):
        """
        Reads all available metadata and returns a dictionary.

        Args:
            verbose: if True, prints the chunks that are not supported.

        Returns:
            dictionary with all metadata.
        """
        metadata = dict()
        for key in self.chunk_dict.keys():
            if key in [b"IMG_SCAN_03", b"@IMG_OBS"]:
                # these chunks have their own dedicated methods for extraction
                continue
            elif key == b"@PARAM_OBS_02":
                metadata["param_obs_02"] = self.read_param_obs()
                continue
            json_key = key.decode().split("@")[-1].lower()
            try:
                metadata[json_key] = self.read_any_info_and_make_dict(key)
            except KeyError:
                if verbose:
                    print(f"{key} there is no method for getting info from this chunk.")
        return metadata

    def read_any_info_and_make_dict(self, chunk_name: str) -> dict:
        """Reads any chunk and constructs a dictionary.

        Args:
            chunk_name: name of the chunk which data will be taken.

        Returns:
            Chunk info data
        """
        if chunk_name not in self.chunk_dict:
            print(f"{chunk_name} is not in chunk list, skipping.")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[chunk_name]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            header_name = f"{chunk_name.decode().split('@')[-1].lower()}_header"
            chunk_info_header = dict(fds_binary.__dict__[header_name].parse(raw))
            chunks_info = dict()
            for idx, key in enumerate(chunk_info_header.keys()):
                if idx == 0:
                    continue
                if type(chunk_info_header[key]) is ListContainer:
                    chunks_info[key] = list(chunk_info_header[key])
                else:
                    chunks_info[key] = chunk_info_header[key]
        return chunks_info

    def read_param_obs(self) -> dict:
        """Reads PARAM_OBS_02 while accounting for varied chunk sizes.

        Returns:
            Chunk info data for PARAM_OBS_02
        """
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@PARAM_OBS_02"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            # PARAM_OBS_02 is either of size 90 or size 6.
            if chunk_size == 90:
                chunk_info_header = dict(fds_binary.param_obs_02_header.parse(raw))
            else:  # chunk_size == 6
                chunk_info_header = dict(
                    fds_binary.param_obs_02_short_header.parse(raw)
                )

            chunks_info = dict()
            for idx, key in enumerate(chunk_info_header.keys()):
                if idx == 0:
                    continue
                if type(chunk_info_header[key]) is ListContainer:
                    chunks_info[key] = list(chunk_info_header[key])
                else:
                    chunks_info[key] = chunk_info_header[key]
        return chunks_info
