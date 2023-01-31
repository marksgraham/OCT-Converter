import io
from pathlib import Path

import numpy as np
from construct import Float64n, Int8un, Int16un, Int32un, PaddedString, Struct
from PIL import Image

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
        hw_info_03_header (obj:Struct) : Defines structure of hw info header
        patient_info_02_header (obj:Struct) : Defines patient info header
        fda_file_info_header (obj:Struct) : Defines fda file info header
        capture_info_02_header (obj:Struct) : Defines capture info header
        param_scan_04_header (obj:Struct) : Defines param scan header
        img_trc_02_header (obj:Struct) : Defines img trc header
        param_obs_02_header (obj:Struct) : Defines param obs header
        img_mot_comp_03_header (obj:Struct) : Defines img mot comp header
        effective_scan_range_header (obj:Struct) : Defines effective scan range header
        regist_info_header (obj:Struct) : Defines regist info header
        result_cornea_curve_header (obj:Struct) : Defines result cornea curve header
        result_cornea_thickness_header (obj:Struct) : Defines result cornea thickness header
        contour_info_header (obj:Struct) : Defines contour info header
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

        self.hw_info_03_header = Struct(
            "model_name" / PaddedString(16, "ascii"),
            "serial_number" / PaddedString(16, "ascii"),
            "zeros" / PaddedString(32, "ascii"),
            "version" / PaddedString(16, "ascii"),
            "build_year" / Int16un,
            "build_month" / Int16un,
            "build_day" / Int16un,
            "build_hour" / Int16un,
            "build_minute" / Int16un,
            "build_second" / Int16un,
            "zeros" / PaddedString(8, "ascii"),
            "version_numbers" / PaddedString(8, "ascii"),
        )

        self.patient_info_02_header = Struct(
            "patient_id" / PaddedString(8, "ascii"),
            "patient_given_name" / PaddedString(8, "ascii"),
            "patient_surname" / PaddedString(8, "ascii"),
            "birth_date_type" / Int8un,
            "birth_year" / Int16un,
            "birth_month" / Int16un,
            "birth_day" / Int16un,
        )

        self.fda_file_info_header = Struct(
            "0x2" / Int32un,
            "0x3e8" / Int32un,
            "8.0.1.20198" / PaddedString(32, "ascii"),
        )

        self.capture_info_02_header = Struct(
            "x" / Int16un,
            "zeros" / PaddedString(52, "ascii"),
            "aquisition_year" / Int16un,
            "aquisition_month" / Int16un,
            "aquisition_day" / Int16un,
            "aquisition_hour" / Int16un,
            "aquisition_minute" / Int16un,
            "aquisition_second" / Int16un,
        )

        self.param_scan_04_header = Struct(
            "tomogram_x_dimension_in_mm" / Float64n,
            "tomogram_y_dimension_in_mm" / Float64n,
            "tomogram_z_dimension_in_um" / Float64n,
        )

        self.img_trc_02_header = Struct(
            "width" / Int32un,
            "height" / Int32un,
            "bits_per_pixel" / Int32un,
            "num_slices_0x2" / Int32un,
            "0x1" / Int8un,
            "size" / Int32un,
        )

        self.param_obs_02_header = Struct(
            "camera_model" / PaddedString(12, "utf16"),
            "jpeg_quality" / Int8un,
            "color_temparature" / Int8un,
        )

        self.img_mot_comp_03_header = Struct(
            "width" / Int32un,
            "height" / Int32un,
            "bits_per_pixel" / Int32un,
            "num_slices" / Int32un,
        )

        self.img_projection_header = Struct(
            "width" / Int32un,
            "height" / Int32un,
            "bits_per_pixel" / Int32un,
            "0x1000002" / Int32un,
            "size" / Int32un,
        )

        self.effective_scan_range_header = Struct(
            "bounding_box_fundus_pixel" / Int32un[4],
            "bounding_box_trc_pixel" / Int32un[4],
        )

        self.regist_info_header = Struct(
            "bounding_box_in_fundus_pixels" / Int32un[4],
            "bounding_box_in_trc_pixels" / Int32un[4],
        )

        self.result_cornea_curve_header = Struct(
            "id" / Int8un[20],
            "width" / Int32un,
            "height" / Int32un,
            "8.0.1.21781" / Int8un[32],
        )

        self.result_cornea_thickness_header = Struct(
            "8.0.1.21781" / Int8un[32],
            "id" / Int8un[20],
            "width" / Int32un,
            "height" / Int32un,
        )

        self.contour_info_header = Struct(
            "id" / Int8un[20],
            "type" / Int16un,
            "width" / Int32un,
            "height" / Int32un,
            "size" / Int32un,
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
                image = Image.open(io.BytesIO(raw_slice))
                slice = np.asarray(image)
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
            image = Image.open(io.BytesIO(raw_image))
            image = np.asarray(image)
        fundus_image = FundusImageWithMetaData(image)
        return fundus_image

    def read_hardware_info(self):
        """Reads hardware info.

        Returns:
            dict:Hardware Info Data
        """
        if b"@HW_INFO_03" not in self.chunk_dict:
            raise ValueError("Could not find fundus header @HW_INFO_03 in chunk list")
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@HW_INFO_03"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            hw_info_03_header = self.hw_info_03_header.parse(raw)
            hw_info_dict = {
                "model_name": str(hw_info_03_header.model_name),
                "serial_number": str(hw_info_03_header.serial_number),
                "zeros": str(hw_info_03_header.zeros),
                "version": str(hw_info_03_header.version),
                "build_year": hw_info_03_header.build_year,
                "build_month": hw_info_03_header.build_month,
                "build_day": hw_info_03_header.build_day,
                "build_hour": hw_info_03_header.build_hour,
                "build_minute": hw_info_03_header.build_minute,
                "build_second": hw_info_03_header.build_second,
                "version_numbers": str(hw_info_03_header.version_numbers),
            }
        return hw_info_dict

    def read_patient_info(self):
        """Reads patient info.

        Returns:
            dict:Patient Info Data
        """
        if b"@PATIENT_INFO_02" not in self.chunk_dict:
            print("@PATIENT_INFO_02 IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@PATIENT_INFO_02"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            patient_info_02_header = self.patient_info_02_header.parse(raw)
            patient_info_dict = {
                "patient_id": str(patient_info_02_header.patient_id),
                "patient_given_name": str(patient_info_02_header.patient_given_name),
                "patient_surname": str(patient_info_02_header.patient_surname),
                "birth_date_type": patient_info_02_header.birth_date_type,
                "birth_year": patient_info_02_header.birth_year,
                "birth_month": patient_info_02_header.birth_month,
                "birth_day": patient_info_02_header.birth_day,
            }
        return patient_info_dict

    def read_fda_file_info(self):
        """Reads fda file info.

        Returns:
            dict:FDA File Info Data
        """
        if b"@FDA_FILE_INFO" not in self.chunk_dict:
            print("@FDA_FILE_INFO IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@FDA_FILE_INFO"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            fda_file_info_header = self.fda_file_info_header.parse(raw)
            fda_file_info_dict = {
                "0x2": fda_file_info_header["0x2"],
                "0x3e8": fda_file_info_header["0x3e8"],
                "8.0.1.20198": fda_file_info_header["8.0.1.20198"],
            }
        return fda_file_info_dict

    def read_capture_info(self):
        """Reads capture info.

        Returns:
            dict:Capture Info Data
        """
        if b"@CAPTURE_INFO_02" not in self.chunk_dict:
            print("@CAPTURE_INFO_02 IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@CAPTURE_INFO_02"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            capture_info_02_header = self.capture_info_02_header.parse(raw)
            capture_info_02_dict = {
                "x": capture_info_02_header.x,
                "zeros": capture_info_02_header.zeros,
                "aquisition year": capture_info_02_header.aquisition_year,
                "aquisition month": capture_info_02_header.aquisition_month,
                "aquisition day": capture_info_02_header.aquisition_day,
                "aquisition hour": capture_info_02_header.aquisition_hour,
                "aquisition minute": capture_info_02_header.aquisition_minute,
                "aquisition second": capture_info_02_header.aquisition_second,
            }
        return capture_info_02_dict

    def read_param_scan(self):
        """Reads param scan info.

        Returns:
            dict:Param Scan Info Data
        """
        if b"@PARAM_SCAN_04" not in self.chunk_dict:
            print("@PARAM_SCAN_04 IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@PARAM_SCAN_04"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            param_scan_04_header = self.param_scan_04_header.parse(raw)
            param_scan_04_dict = {
                "tomogram x dimension in mm": param_scan_04_header.tomogram_x_dimension_in_mm,
                "tomogram y dimension in mm": param_scan_04_header.tomogram_y_dimension_in_mm,
                "tomogram z dimension in um": param_scan_04_header.tomogram_z_dimension_in_um,
            }
        return param_scan_04_dict

    def read_fundus_image_gray_scale(self):
        """Reads gray scale fundus image.

        Returns:
            obj:FundusImageWithMetaData
        """
        if b"@IMG_TRC_02" not in self.chunk_dict:
            print("@IMG_TRC_02 IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@IMG_TRC_02"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read(21)  # skip 21 is important
            img_trc_02_header = self.img_trc_02_header.parse(raw)
            number_pixels = img_trc_02_header.width * img_trc_02_header.height * 1
            raw_image = f.read(img_trc_02_header.size)
            image = Image.open(io.BytesIO(raw_image))
            image = np.asarray(image)
        fundus_gray_scale_image = FundusImageWithMetaData(image)
        return fundus_gray_scale_image

    def read_param_obs(self):
        """Reads param obs info.

        Returns:
            dict:Param OBS Info Data
        """
        if b"@PARAM_OBS_02" not in self.chunk_dict:
            print("@PARAM_OBS_02 IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@PARAM_OBS_02"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read(16)
            param_obs_02_header = self.param_obs_02_header.parse(raw)
            param_obs_02_dict = {
                "jpeg fine": param_obs_02_header.jpeg_quality,
                "color temparature": param_obs_02_header.color_temparature,
            }
        return param_obs_02_dict

    def read_img_mot_comp(self):
        """Reads img mot comp info.

        Returns:
            dict:IMG MOT COMP Info Data
        """
        if b"@IMG_MOT_COMP_03" not in self.chunk_dict:
            print("@IMG_MOT_COMP_03 IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@IMG_MOT_COMP_03"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            img_mot_comp_03_header = self.img_mot_comp_03_header.parse(raw)
            img_mot_comp_03_dict = {
                "width": img_mot_comp_03_header.width,
                "height": img_mot_comp_03_header.height,
                "bits per pixel": img_mot_comp_03_header.bits_per_pixel,
                "num slices": img_mot_comp_03_header.num_slices,
            }
        return img_mot_comp_03_dict

    def read_img_projection(self):
        """Reads img projection info.

        Returns:
            dict:IMG PROJECTION Info Data
        """
        if b"@IMG_PROJECTION" not in self.chunk_dict:
            print("@IMG_PROJECTION IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@IMG_PROJECTION"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            img_projection_header = self.img_projection_header.parse(raw)
            img_projection_dict = {
                "width": img_projection_header.width,
                "height": img_projection_header.height,
                "bits per pixel": img_projection_header.bits_per_pixel,
                "size": img_projection_header.size,
            }
        return img_projection_dict

    def read_effective_scan_range(self):
        """Reads effective scan range info.

        Returns:
            dict:Effective Scan Range Info Data
        """
        if b"@EFFECTIVE_SCAN_RANGE" not in self.chunk_dict:
            print("@EFFECTIVE_SCAN_RANGE IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@EFFECTIVE_SCAN_RANGE"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            effective_scan_range_header = self.effective_scan_range_header.parse(raw)
            effective_scan_range_dict = {
                "bounding_box_fundus_pixel": list(
                    effective_scan_range_header.bounding_box_fundus_pixel
                ),
                "bounding_box_trc_pixel": list(
                    effective_scan_range_header.bounding_box_trc_pixel
                ),
            }
        return effective_scan_range_dict

    def read_regist_info(self):
        """Reads regist info.

        Returns:
            dict:Regist Info Data
        """
        if b"@REGIST_INFO" not in self.chunk_dict:
            print("@REGIST_INFO IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@REGIST_INFO"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            regist_info_header = self.regist_info_header.parse(raw)
            regist_info_dict = {
                "bbox_in_fundus_pixel(min,max,x,y or center,x,y,radius)": list(
                    regist_info_header.bounding_box_in_fundus_pixels
                ),
                "bbox_in_trc_pixel(min,max,x,y or center,x,y,radius)": list(
                    regist_info_header.bounding_box_in_trc_pixels
                ),
            }
        return regist_info_dict

    def read_cornea_curve_result_info(self):
        """Reads result cornea curve info.

        Returns:
            dict:Result Cornea Curve Info Data
        """
        if b"@RESULT_CORNEA_CURVE" not in self.chunk_dict:
            print("@RESULT_CORNEA_CURVE IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@RESULT_CORNEA_CURVE"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            result_cornea_curve_header = self.result_cornea_curve_header.parse(raw)
            result_cornea_curve_dict = {
                "id": result_cornea_curve_header.id,
                "width": result_cornea_curve_header.width,
                "height": result_cornea_curve_header.height,
                "8.0.1.21781": result_cornea_curve_header["8.0.1.21781"],
            }
        return result_cornea_curve_dict

    def read_result_cornea_thickness(self):
        """Reads result cornea thickness info.

        Returns:
            dict:Result Cornea Thickness Info Data
        """
        if b"@RESULT_CORNEA_THICKNESS" not in self.chunk_dict:
            print("@RESULT_CORNEA_THICKNESS IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@RESULT_CORNEA_THICKNESS"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            result_cornea_thickness_header = self.result_cornea_thickness_header.parse(
                raw
            )
            result_cornea_thickness_dict = {
                "id": result_cornea_thickness_header.id,
                "width": result_cornea_thickness_header.width,
                "height": result_cornea_thickness_header.height,
                "8.0.1.21781": result_cornea_thickness_header["8.0.1.21781"],
            }
        return result_cornea_thickness_dict

    def read_contour_info(self):
        """Reads contour info.

        Returns:
            dict:Contour Info Data
        """
        if b"@CONTOUR_INFO" not in self.chunk_dict:
            print("@CONTOUR_INFO IS NOT IN CHUNKS SKIPPING...")
            return None
        with open(self.filepath, "rb") as f:
            chunk_location, chunk_size = self.chunk_dict[b"@CONTOUR_INFO"]
            f.seek(chunk_location)  # Set the chunk’s current position.
            raw = f.read()
            contour_info_header = self.contour_info_header.parse(raw)
            contour_info_dict = {
                "id": contour_info_header.id,
                "type": contour_info_header.type,
                "width": contour_info_header.width,
                "height": contour_info_header.height,
                "size": contour_info_header.size,
            }
        return contour_info_dict
