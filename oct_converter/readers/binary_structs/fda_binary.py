from construct import Float32n, Float64n, Int8un, Int16un, Int32un, PaddedString, Struct

"""
        Notes:
        Mostly based on description of .fda file format here:
        https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format

        header (obj:Struct): Defines structure of volume's header.
        oct_header (obj:Struct): Defines structure of OCT header.
        fundus_header (obj:Struct): Defines structure of fundus header.
        chunk_dict (dict): Name of data chunks present in the file, and their start locations.
        hw_info_03_header (obj:Struct) : Defines structure of hw info header
        patient_info_02_header (obj:Struct) : Defines patient info header
        file_info_header (obj:Struct) : Defines fda file info header
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
        align_info_header (obj:Struct) : Defines align info header
        fast_q2_info_header (obj:Struct) : Defines fast q2 info header
        gla_littmann_01_header (obj : Struct) : Defines gla littmann 01 header
"""

header = Struct(
    "FOCT" / PaddedString(4, "ascii"),
    "FDA" / PaddedString(3, "ascii"),
    "version_info_1" / Int32un,
    "version_info_2" / Int32un,
)

oct_header = Struct(
    "type" / PaddedString(1, "ascii"),
    "unknown1" / Int32un,
    "unknown2" / Int32un,
    "width" / Int32un,
    "height" / Int32un,
    "number_slices" / Int32un,
    "unknown3" / Int32un,
)

oct_header_2 = Struct(
    "unknown" / PaddedString(1, "ascii"),
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "number_slices" / Int32un,
    "unknown" / PaddedString(1, "ascii"),
    "size" / Int32un,
)

fundus_header = Struct(
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "number_slices" / Int32un,
    "unknown" / PaddedString(4, "ascii"),
    "size" / Int32un,
    # 'img' / Int8un,
)

hw_info_03_header = Struct(
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

patient_info_02_header = Struct(
    "patient_id" / PaddedString(8, "ascii"),
    "patient_given_name" / PaddedString(8, "ascii"),
    "patient_surname" / PaddedString(8, "ascii"),
    "birth_date_type" / Int8un,
    "birth_year" / Int16un,
    "birth_month" / Int16un,
    "birth_day" / Int16un,
)

file_info_header = Struct(
    "0x2" / Int32un,
    "0x3e8" / Int32un,
    "8.0.1.20198" / PaddedString(32, "ascii"),
)

capture_info_02_header = Struct(
    "x" / Int16un,
    "zeros" / PaddedString(52, "ascii"),
    "aquisition_year" / Int16un,
    "aquisition_month" / Int16un,
    "aquisition_day" / Int16un,
    "aquisition_hour" / Int16un,
    "aquisition_minute" / Int16un,
    "aquisition_second" / Int16un,
)

param_scan_04_header = Struct(
    "unknown" / Int16un[6],
    "tomogram_x_dimension_in_mm" / Float64n,
    "tomogram_y_dimension_in_mm" / Float64n,
    "tomogram_z_dimension_in_um" / Float64n,
)

img_trc_02_header = Struct(
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "num_slices_0x2" / Int32un,
    "0x1" / Int8un,
    "size" / Int32un,
)

param_obs_02_header = Struct(
    "camera_model" / PaddedString(12, "utf16"),
    "jpeg_quality" / Int8un,
    "color_temparature" / Int8un,
)

img_mot_comp_03_header = Struct(
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "num_slices" / Int32un,
)

img_projection_header = Struct(
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "0x1000002" / Int32un,
    "size" / Int32un,
)

effective_scan_range_header = Struct(
    "bounding_box_fundus_pixel" / Int32un[4],
    "bounding_box_trc_pixel" / Int32un[4],
)

regist_info_header = Struct(
    "bounding_box_in_fundus_pixels" / Int32un[4],
    "bounding_box_in_trc_pixels" / Int32un[4],
)

result_cornea_curve_header = Struct(
    "id" / Int8un[20],
    "width" / Int32un,
    "height" / Int32un,
    "8.0.1.21781" / Int8un[32],
)

result_cornea_thickness_header = Struct(
    "8.0.1.21781" / Int8un[32],
    "id" / Int8un[20],
    "width" / Int32un,
    "height" / Int32un,
)

contour_info_header = Struct(
    "id" / PaddedString(20, "ascii"),
    "type" / Int16un,
    "width" / Int32un,
    "height" / Int32un,
    "size" / Int32un,
)

fast_q2_info_header = Struct("various_quality_statistics" / Float32n[6])

gla_littmann_01_header = Struct("0xffff" / Int32un, "0x1" / Int32un)
