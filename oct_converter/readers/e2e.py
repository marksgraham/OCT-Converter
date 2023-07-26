from __future__ import annotations

import warnings
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import chain
from pathlib import Path

import numpy as np

from oct_converter.image_types import FundusImageWithMetaData, OCTVolumeWithMetaData
from oct_converter.readers.binary_structs import e2e_binary


class E2E(object):
    """Class for extracting data from Heidelberg's .e2e file format.

    Notes:
        Mostly based on description of .e2e file format here:
        https://bitbucket.org/uocte/uocte/wiki/Heidelberg%20File%20Format.

    Attributes:
        filepath: path to .e2e file for reading.
    """

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)

        self.power = pow(2, 10)
        self.sex = None
        self.first_name = None
        self.surname = None
        self.acquisition_date = None

    def read_oct_volume(
        self, legacy_intensity_transform: bool = False
    ) -> list[OCTVolumeWithMetaData]:
        """Reads OCT data.

        Args:
            legacy_intensity_transform: if True, use intensity transform used in v<=0.5.7. Defaults to False.

        Returns:
            A list of OCTVolumeWithMetaData.
        """

        def _make_lut():
            LUT = []
            for i in range(0, pow(2, 16)):
                LUT.append(self.uint16_to_ufloat16(i))
            return np.array(LUT)

        LUT = _make_lut()

        with open(self.filepath, "rb") as f:
            raw = f.read(21)
            if raw == b"E2EMultipleVolumeFile":
                self.byte_skip = 64
            else:
                self.byte_skip = 0
            f.seek(self.byte_skip)
            raw = f.read(36)

            header = e2e_binary.header_structure.parse(raw)
            raw = f.read(52)
            main_directory = e2e_binary.main_directory_structure.parse(raw)

            # traverse list of main directories in first pass
            directory_stack = []

            current = main_directory.current
            while current != 0:
                directory_stack.append(current)
                f.seek(current + self.byte_skip)
                raw = f.read(52)
                directory_chunk = e2e_binary.main_directory_structure.parse(raw)
                current = directory_chunk.prev

            # traverse in second pass and  get all subdirectories
            chunk_stack = []
            volume_dict = {}
            for position in directory_stack:
                f.seek(position + self.byte_skip)
                raw = f.read(52)
                directory_chunk = e2e_binary.main_directory_structure.parse(raw)

                for ii in range(directory_chunk.num_entries):
                    raw = f.read(44)
                    chunk = e2e_binary.sub_directory_structure.parse(raw)
                    volume_string = "{}_{}_{}".format(
                        chunk.patient_id, chunk.study_id, chunk.series_id
                    )
                    if volume_string not in volume_dict.keys():
                        volume_dict[volume_string] = chunk.slice_id / 2
                    elif chunk.slice_id / 2 > volume_dict[volume_string]:
                        volume_dict[volume_string] = chunk.slice_id / 2

                    if chunk.start > chunk.pos:
                        chunk_stack.append([chunk.start, chunk.size])

            # initalise dict to hold all the image volumes
            volume_array_dict = {}
            volume_array_dict_additional = (
                {}
            )  # for storage of slices not caught by extraction
            laterality_dict = {}
            laterality = None
            for volume, num_slices in volume_dict.items():
                if num_slices > 0:
                    # num_slices + 1 here due to evidence that a slice was being missed off the end in extraction
                    volume_array_dict[volume] = [0] * int(num_slices + 1)

            contour_dict = defaultdict(lambda: defaultdict(dict))

            # traverse all chunks and extract slices
            for start, pos in chunk_stack:
                f.seek(start + self.byte_skip)
                raw = f.read(60)
                chunk = e2e_binary.chunk_structure.parse(raw)

                if chunk.type == 9:  # patient data
                    raw = f.read(127)
                    try:
                        patient_data = e2e_binary.patient_id_structure.parse(raw)
                        self.sex = patient_data.sex
                        self.first_name = patient_data.first_name
                        self.surname = patient_data.surname
                        # this gives the birthdate as a Julian date, needs converting to calendar date
                        self.birthdate = (patient_data.birthdate / 64) - 14558805
                        self.patient_id = patient_data.patient_id
                    except Exception:
                        pass

                elif chunk.type == 10004:  # bscan metadata
                    raw = f.read(104)
                    bscan_metadata = e2e_binary.bscan_metadata.parse(raw)
                    start_epoch = datetime(
                        year=1600, month=12, day=31, hour=23, minute=59
                    )
                    acquisition_datetime = start_epoch + timedelta(
                        seconds=bscan_metadata.acquisitionTime * 1e-7
                    )
                    if self.acquisition_date is None:
                        self.acquisition_date = acquisition_datetime.date()

                elif chunk.type == 11:  # laterality data
                    raw = f.read(20)
                    try:
                        laterality_data = e2e_binary.lat_structure.parse(raw)
                        if laterality_data.laterality == 82:
                            laterality = "R"
                        elif laterality_data.laterality == 76:
                            laterality = "L"
                    except Exception:
                        laterality = None

                elif chunk.type == 10019:  # contour data
                    raw = f.read(16)
                    contour_data = e2e_binary.contour_structure.parse(raw)

                    if contour_data.width > 0:
                        volume_string = "{}_{}_{}".format(
                            chunk.patient_id, chunk.study_id, chunk.series_id
                        )
                        slice_id = int(chunk.slice_id / 2) - 1
                        contour_name = f"contour{contour_data.id}"
                        try:
                            raw_volume = np.frombuffer(
                                f.read(contour_data.width * 4), dtype=np.float32
                            )
                            contour = np.array(raw_volume)
                            max_float = np.finfo(np.float32).max
                            contour[(contour < 1e-9) | (contour == max_float)] = np.nan
                        except Exception as e:
                            warnings.warn(
                                (
                                    f"Could not read contour "
                                    f"image id {volume_string}"
                                    f"contour name {contour_name} "
                                    f"slice id {slice_id}."
                                ),
                                UserWarning,
                            )
                        else:
                            (
                                contour_dict[volume_string][contour_name][slice_id]
                            ) = contour

                elif chunk.type == 1073741824:  # image data
                    raw = f.read(20)
                    image_data = e2e_binary.image_structure.parse(raw)

                    if chunk.ind == 1:  # oct data
                        count = image_data.height * image_data.width
                        if count == 0:
                            break
                        raw_volume = np.fromfile(f, dtype=np.uint16, count=count)
                        volume_string = "{}_{}_{}".format(
                            chunk.patient_id, chunk.study_id, chunk.series_id
                        )
                        try:
                            image = LUT[raw_volume].reshape(
                                image_data.height, image_data.width
                            )
                        except Exception:
                            warnings.warn(
                                (
                                    f"Could not reshape image id {volume_string} with "
                                    f"{len(LUT[raw_volume])} elements into a "
                                    f"{image_data.height}x"
                                    f"{image_data.width} array"
                                ),
                                UserWarning,
                            )
                        else:
                            if legacy_intensity_transform:
                                image = pow(image, 1.0 / 2.4)
                            else:
                                image = self.vol_intensity_transform(image)

                            if volume_string in volume_array_dict.keys():
                                volume_array_dict[volume_string][
                                    int(chunk.slice_id / 2) - 1
                                ] = image
                            else:
                                # try to capture these additional images
                                if volume_string in volume_array_dict_additional.keys():
                                    volume_array_dict_additional[volume_string].append(
                                        image
                                    )
                                else:
                                    volume_array_dict_additional[volume_string] = [
                                        image
                                    ]
                            # here assumes laterality stored in chunk before the image itself
                            if laterality and volume_string not in laterality_dict:
                                laterality_dict[volume_string] = laterality

            contour_data = {}
            for volume_id, contours in contour_dict.items():
                if volume_id in volume_dict:
                    num_slices = int(volume_dict[volume_id]) + 1
                else:
                    num_slices = None
                contour_data[volume_id] = {
                    k: [None] * (num_slices or len(v)) for k, v in contours.items()
                }

                for contour_name, contour_values in contours.items():
                    for slice_id, contour in contour_values.items():
                        (contour_data[volume_id][contour_name][slice_id]) = contour

            oct_volumes = []
            for key, volume in chain(
                volume_array_dict.items(), volume_array_dict_additional.items()
            ):
                # remove any initalised volumes that never had image data attached
                volume = [slc for slc in volume if not isinstance(slc, int)]
                if volume is None or len(volume) == 0:
                    continue
                oct_volumes.append(
                    OCTVolumeWithMetaData(
                        volume=volume,
                        patient_id=self.patient_id,
                        first_name=self.first_name,
                        surname=self.surname,
                        sex=self.sex,
                        acquisition_date=self.acquisition_date,
                        volume_id=key,
                        laterality=laterality_dict.get(key),
                        contours=contour_data.get(key),
                    )
                )

        return oct_volumes

    def read_fundus_image(self) -> list[FundusImageWithMetaData]:
        """Reads fundus data.

        Returns:
            A sequence of FundusImageWithMetaData.
        """
        with open(self.filepath, "rb") as f:
            raw = f.read(21)
            if raw == b"E2EMultipleVolumeFile":
                self.byte_skip = 64
            else:
                self.byte_skip = 0
            f.seek(self.byte_skip)
            raw = f.read(36)
            header = e2e_binary.header_structure.parse(raw)
            raw = f.read(52)
            main_directory = e2e_binary.main_directory_structure.parse(raw)

            # traverse list of main directories in first pass
            directory_stack = []

            laterality = None

            current = main_directory.current
            while current != 0:
                directory_stack.append(current)
                f.seek(current + self.byte_skip)
                raw = f.read(52)
                directory_chunk = e2e_binary.main_directory_structure.parse(raw)
                current = directory_chunk.prev

            # traverse in second pass and  get all subdirectories
            chunk_stack = []
            for position in directory_stack:
                f.seek(position + self.byte_skip)
                raw = f.read(52)
                directory_chunk = e2e_binary.main_directory_structure.parse(raw)

                for ii in range(directory_chunk.num_entries):
                    raw = f.read(44)
                    chunk = e2e_binary.sub_directory_structure.parse(raw)
                    if chunk.start > chunk.pos:
                        chunk_stack.append([chunk.start, chunk.size])

            # initalise dict to hold all the image volumes
            image_array_dict = {}
            laterality_dict = {}

            # traverse all chunks and extract slices
            for start, pos in chunk_stack:
                f.seek(start + self.byte_skip)
                raw = f.read(60)
                chunk = e2e_binary.chunk_structure.parse(raw)

                if chunk.type == 9:  # patient data
                    raw = f.read(127)
                    try:
                        patient_data = e2e_binary.patient_id_structure.parse(raw)
                        self.sex = patient_data.sex
                        self.first_name = patient_data.first_name
                        self.surname = patient_data.surname
                        # this gives the birthdate as a Julian date, needs converting to calendar date
                        self.birthdate = (patient_data.birthdate / 64) - 14558805
                        self.patient_id = patient_data.patient_id
                    except Exception:
                        pass

                if chunk.type == 11:  # laterality data
                    raw = f.read(20)
                    try:
                        laterality_data = e2e_binary.lat_structure.parse(raw)
                        if laterality_data.laterality == 82:
                            laterality = "R"
                        elif laterality_data.laterality == 76:
                            laterality = "L"
                    except Exception:
                        laterality = None

                if chunk.type == 1073741824:  # image data
                    raw = f.read(20)
                    image_data = e2e_binary.image_structure.parse(raw)
                    count = image_data.height * image_data.width
                    if count == 0:
                        break
                    if chunk.ind == 0:  # fundus data
                        raw_volume = np.frombuffer(f.read(count), dtype=np.uint8)
                        image = np.array(raw_volume).reshape(
                            image_data.height, image_data.width
                        )
                        image_string = "{}_{}_{}".format(
                            chunk.patient_id, chunk.study_id, chunk.series_id
                        )
                        image_array_dict[image_string] = image
                        # here assumes laterality stored in chunk before the image itself
                        laterality_dict[image_string] = laterality
            fundus_images = []
            for key, image in image_array_dict.items():
                fundus_images.append(
                    FundusImageWithMetaData(
                        image=image,
                        patient_id=self.patient_id,
                        image_id=key,
                        laterality=laterality_dict[key]
                        if key in laterality_dict.keys()
                        else None,
                    )
                )

        return fundus_images

    def read_custom_float(self, bytes: str) -> float:
        """Implementation of bespoke float type used in .e2e files.

        Notes:
            Custom float is a floating point type with no sign, 6-bit exponent, and 10-bit mantissa.

        Args:
            bytes: the two bytes.

        Returns:
            float
        """
        # convert two bytes to 16-bit binary representation
        bits = bin(bytes[0])[2:].zfill(8)[::-1] + bin(bytes[1])[2:].zfill(8)[::-1]

        # get mantissa and exponent
        mantissa = bits[:10]
        exponent = bits[10:]

        # convert to decimal representations
        mantissa_sum = 1 + int(mantissa, 2) / self.power
        exponent_sum = int(exponent[::-1], 2) - 63
        decimal_value = mantissa_sum * pow(2, exponent_sum)
        return decimal_value

    def uint16_to_ufloat16(self, uint16: int) -> float:
        """Implementation of bespoke float type used in .e2e files.

        Notes:
            Custom float is a floating point type with no sign, 6-bit exponent, and 10-bit mantissa.

        Args:
            uint16

        Returns:
            float
        """
        bits = "{0:016b}".format(uint16)[::-1]
        # get mantissa and exponent
        mantissa = bits[:10]
        exponent = bits[10:]
        exponent = exponent[::-1]

        # convert to decimal representations
        mantissa_sum = 1 + int(mantissa, 2) / self.power
        exponent_sum = int(exponent, 2) - 63
        decimal_value = mantissa_sum * np.float_power(2, exponent_sum)
        return decimal_value

    def vol_intensity_transform(self, data: np.array) -> np.array:
        """Implementation of intensity transform used in .e2e files.

        Notes:
            Code thanks to @oli4, see discussion in https://github.com/marksgraham/OCT-Converter/issues/21#issuecomment-1057455183
        """
        selection_0 = data == np.finfo(np.float32).max
        selection_data = data <= 1

        new = np.log(data[selection_data] + 2.44e-04)
        new = (new + 8.3) / 8.285

        data[selection_data] = new
        data[selection_0] = 0
        data = np.clip(data, 0, 1)
        return data
