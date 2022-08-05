import warnings
from collections import defaultdict
from itertools import chain
from pathlib import Path

import numpy as np
from construct import Array, Int8un, Int16un, Int32sn, Int32un, PaddedString, Struct

from oct_converter.image_types import FundusImageWithMetaData, OCTVolumeWithMetaData


class E2E(object):
    """Class for extracting data from Heidelberg's .e2e file format.

    Notes:
        Mostly based on description of .e2e file format here:
        https://bitbucket.org/uocte/uocte/wiki/Heidelberg%20File%20Format.

    Attributes:
        filepath (str): Path to .img file for reading.
        header_structure (obj:Struct): Defines structure of volume's header.
        main_directory_structure (obj:Struct): Defines structure of volume's main directory.
        sub_directory_structure (obj:Struct): Defines structure of each sub directory in the volume.
        chunk_structure (obj:Struct): Defines structure of each data chunk.
        image_structure (obj:Struct): Defines structure of image header.
    """

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)
        self.header_structure = Struct(
            "magic1" / PaddedString(12, "ascii"),
            "version" / Int32un,
            "unknown" / Array(10, Int16un),
        )
        self.main_directory_structure = Struct(
            "magic2" / PaddedString(12, "ascii"),
            "version" / Int32un,
            "unknown" / Array(10, Int16un),
            "num_entries" / Int32un,
            "current" / Int32un,
            "prev" / Int32un,
            "unknown3" / Int32un,
        )
        self.sub_directory_structure = Struct(
            "pos" / Int32un,
            "start" / Int32un,
            "size" / Int32un,
            "unknown" / Int32un,
            "patient_id" / Int32un,
            "study_id" / Int32un,
            "series_id" / Int32un,
            "slice_id" / Int32sn,
            "unknown2" / Int16un,
            "unknown3" / Int16un,
            "type" / Int32un,
            "unknown4" / Int32un,
        )
        self.chunk_structure = Struct(
            "magic3" / PaddedString(12, "ascii"),
            "unknown" / Int32un,
            "unknown2" / Int32un,
            "pos" / Int32un,
            "size" / Int32un,
            "unknown3" / Int32un,
            "patient_id" / Int32un,
            "study_id" / Int32un,
            "series_id" / Int32un,
            "slice_id" / Int32sn,
            "ind" / Int16un,
            "unknown4" / Int16un,
            "type" / Int32un,
            "unknown5" / Int32un,
        )
        self.image_structure = Struct(
            "size" / Int32un,
            "type" / Int32un,
            "unknown" / Int32un,
            "width" / Int32un,
            "height" / Int32un,
        )
        self.patient_id_structure = Struct(
            "first_name" / PaddedString(31, "ascii"),
            "surname" / PaddedString(66, "ascii"),
            "birthdate" / Int32un,
            "sex" / PaddedString(1, "ascii"),
            "patient_id" / PaddedString(25, "ascii"),
        )
        self.lat_structure = Struct(
            "unknown" / Array(14, Int8un), "laterality" / Int8un, "unknown2" / Int8un
        )
        self.contour_structure = Struct(
            "unknown0" / Int32un,
            "id" / Int32un,
            "unknown1" / Int32un,
            "width" / Int32un,
        )

        self.power = pow(2, 10)
        self.sex = None
        self.first_name = None
        self.surname = None

    def read_oct_volume(self):
        """Reads OCT data.

        Returns:
            obj:OCTVolumeWithMetaData
        """

        def _make_lut():
            LUT = []
            for i in range(0, pow(2, 16)):
                LUT.append(self.uint16_to_ufloat16(i))
            return np.array(LUT)

        LUT = _make_lut()

        with open(self.filepath, "rb") as f:
            raw = f.read(36)
            header = self.header_structure.parse(raw)

            raw = f.read(52)
            main_directory = self.main_directory_structure.parse(raw)

            # traverse list of main directories in first pass
            directory_stack = []

            current = main_directory.current
            while current != 0:
                directory_stack.append(current)
                f.seek(current)
                raw = f.read(52)
                directory_chunk = self.main_directory_structure.parse(raw)
                current = directory_chunk.prev

            # traverse in second pass and  get all subdirectories
            chunk_stack = []
            volume_dict = {}
            for position in directory_stack:
                f.seek(position)
                raw = f.read(52)
                directory_chunk = self.main_directory_structure.parse(raw)

                for ii in range(directory_chunk.num_entries):
                    raw = f.read(44)
                    chunk = self.sub_directory_structure.parse(raw)
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
                f.seek(start)
                raw = f.read(60)
                chunk = self.chunk_structure.parse(raw)

                if chunk.type == 9:  # patient data
                    raw = f.read(127)
                    try:
                        patient_data = self.patient_id_structure.parse(raw)
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
                        laterality_data = self.lat_structure.parse(raw)
                        if laterality_data.laterality == 82:
                            laterality = "R"
                        elif laterality_data.laterality == 76:
                            laterality = "L"
                    except Exception:
                        laterality = None

                if chunk.type == 10019:  # contour data
                    raw = f.read(16)
                    contour_data = self.contour_structure.parse(raw)

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

                if chunk.type == 1073741824:  # image data
                    raw = f.read(20)
                    image_data = self.image_structure.parse(raw)

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
                                image_data.width, image_data.height
                            )
                        except Exception:
                            warnings.warn(
                                (
                                    f"Could not reshape image id {volume_string} with "
                                    f"{len(LUT[raw_volume])} elements into a "
                                    f"{image_data.width}x"
                                    f"{image_data.height} array"
                                ),
                                UserWarning,
                            )
                        else:
                            image = 256 * pow(image, 1.0 / 2.4)

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
                if isinstance(volume[0], int):
                    continue
                oct_volumes.append(
                    OCTVolumeWithMetaData(
                        volume=volume,
                        patient_id=self.patient_id,
                        volume_id=key,
                        laterality=laterality_dict.get(key),
                        sex=self.sex,
                        first_name=self.first_name,
                        surname=self.surname,
                        contours=contour_data.get(key),
                    )
                )

        return oct_volumes

    def read_fundus_image(self):
        """Reads fundus data.

        Returns:
            obj:FundusImageWithMetaData
        """
        with open(self.filepath, "rb") as f:
            raw = f.read(36)
            header = self.header_structure.parse(raw)

            raw = f.read(52)
            main_directory = self.main_directory_structure.parse(raw)

            # traverse list of main directories in first pass
            directory_stack = []

            laterality = None

            current = main_directory.current
            while current != 0:
                directory_stack.append(current)
                f.seek(current)
                raw = f.read(52)
                directory_chunk = self.main_directory_structure.parse(raw)
                current = directory_chunk.prev

            # traverse in second pass and  get all subdirectories
            chunk_stack = []
            for position in directory_stack:
                f.seek(position)
                raw = f.read(52)
                directory_chunk = self.main_directory_structure.parse(raw)

                for ii in range(directory_chunk.num_entries):
                    raw = f.read(44)
                    chunk = self.sub_directory_structure.parse(raw)
                    if chunk.start > chunk.pos:
                        chunk_stack.append([chunk.start, chunk.size])

            # initalise dict to hold all the image volumes
            image_array_dict = {}
            laterality_dict = {}

            # traverse all chunks and extract slices
            for start, pos in chunk_stack:
                f.seek(start)
                raw = f.read(60)
                chunk = self.chunk_structure.parse(raw)

                if chunk.type == 9:  # patient data
                    raw = f.read(127)
                    try:
                        patient_data = self.patient_id_structure.parse(raw)
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
                        laterality_data = self.lat_structure.parse(raw)
                        if laterality_data.laterality == 82:
                            laterality = "R"
                        elif laterality_data.laterality == 76:
                            laterality = "L"
                    except Exception:
                        laterality = None

                if chunk.type == 1073741824:  # image data
                    raw = f.read(20)
                    image_data = self.image_structure.parse(raw)
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

    def read_custom_float(self, bytes):
        """Implementation of bespoke float type used in .e2e files.

        Notes:
            Custom float is a floating point type with no sign, 6-bit exponent, and 10-bit mantissa.

        Args:
            bytes (str): The two bytes.

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

    def uint16_to_ufloat16(self, uint16):
        """Implementation of bespoke float type used in .e2e files.

        Notes:
            Custom float is a floating point type with no sign, 6-bit exponent, and 10-bit mantissa.

        Args:
            uint16 (int):

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
