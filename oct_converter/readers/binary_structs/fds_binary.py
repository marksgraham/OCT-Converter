from construct import (
    Array,
    Float32n,
    Float64n,
    Int8un,
    Int16un,
    Int32un,
    PaddedString,
    Struct,
    this,
)

"""
        Notes:
        Mostly based on description of .fds file format here:
        https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format

        header (obj:Struct) : Defines structure of volume's header.
        oct_header (obj:Struct) : Defines structure of OCT header (IMG_SCAN_03).
        oct_header_2 (obj:Struct) : Defines structure of OCT header (IMG_SCAN_02).
        fundus_header (obj:Struct): Defines structure of fundus header (IMG_OBS).
        param_scan_04_header (obj:Struct) : Defines PARAM_SCAN_04 header.
        param_scan_02_header (obj:Struct) : Defines PARAM_SCAN_02 header.
        hw_info_03_header (obj:Struct) : Defines HW_INFO_03 header.
        hw_info_02_header (obj:Struct) : Defines HW_INFO_02 header.
        hw_info_01_header (obj:Struct) : Defines HW_INFO_01 header.
        patient_info_02_header (obj:Struct) : Defines PATIENT_INFO_02 header.
        file_info_header (obj:Struct) : Defines FILE_INFO header.
        capture_info_02_header (obj:Struct) : Defines CAPTURE_INFO_02 header.
        capture_info_header (obj:Struct) : Defines CAPTURE_INFO header.
        img_trc_02_header (obj:Struct) : Defines IMG_TRC_02 header.
        img_trc_header (obj:Struct) : Defines IMG_TRC header.
        param_obs_02_header (obj:Struct) : Defines PARAM_OBS_02 when size is 90.
        param_obs_02_short_header (obj:Struct) : Defines PARAM_OBS_02 when size is 6.
        param_trc_02_header (obj:Struct) : Defines PARAM_TRC_02 header.
        img_mot_comp_03_header (obj:Struct) : Defines IMG_MOT_COMP_03 header.
        img_mot_comp_02_header (obj:Struct) : Defines IMG_MOT_COMP_02 header.
        img_mot_comp_header (obj:Struct) : Defines IMG_MOT_COMP header.
        img_projection_header (obj:Struct) : Defines IMG_PROJECTION header.
        effective_scan_range_header (obj:Struct) : Defines EFFECTIVE_SCAN_RANGE header.
        regist_info_header (obj:Struct) : Defines REGIST_INFO header.
        regist_scan_02_header (obj:Struct) : Defines REGIST_SCAN_02 header.
        result_cornea_curve_header (obj:Struct) : Defines RESULT_CORNEA_CURVE header.
        result_cornea_thickness_header (obj:Struct) : Defines RESULT_CORNEA_THICKNESS header.
        align_info_header (obj:Struct) : Defines ALIGN_INFO header.
        main_module_info_header (obj:Struct) : Defines MAIN_MODULE_INFO header.
        fast_q2_info_header (obj:Struct) : Defines FAST_Q2_INFO header.
        gla_littmann_01_header (obj:Struct) : Defines GLA_LITTMANN_01 header.
        thumbnail_header (obj:Struct) : Defines THUMBNAIL header.
        patientext_info_header (obj:Struct) : Defines PATIENTEXT_INFO header.
"""

header = Struct(
    "file_code" / PaddedString(4, "ascii"),  # Always "FOCT"
    "file_type" / PaddedString(3, "ascii"),
    # file_type is "FDA" or "FAA",
    # denoting "macula" or "external" fixation
    "major_ver" / Int32un,
    "minor_ver" / Int32un,
)

# IMG_SCAN_03
oct_header = Struct(
    "scan_mode" / Int8un,  # 2 = 3D, 3 = Radial, 4 = Cross
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "number_slices" / Int32un,
    "format" / Int8un,
    "size" / Int32un,
)

# IMG_SCAN_02
oct_header_2 = Struct(
    "scan_mode" / Int8un,  # 2 = 3D, 3 = Radial, 4 = Cross
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "number_slices" / Int32un,
    "fast_q" / Float64n,
    "format" / Int8un,
    "size" / Int32un,
)

# IMG_OBS
fundus_header = Struct(
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "number_slices" / Int32un,
    "format" / Int8un,
    "size" / Int32un,
)

param_scan_04_header = Struct(
    "fixation" / Int32un,
    "mirror_pos" / Int32un,
    "polar" / Int32un,
    "x_dimension_mm" / Float64n,
    "y_dimension_mm" / Float64n,
    "z_resolution_um" / Float64n,
    "comp_eff_2" / Float64n,
    "comp_eff_3" / Float64n,
    "base_pos" / Int8un,
    "used_calib_data" / Int8un,
)

param_scan_02_header = Struct(
    "scan_mode" / Int8un,
    "light_level" / Int32un,
    "fixation" / Int32un,
    "mirror_pos" / Int32un,
    "nd" / Int32un,
    "polar" / Int32un,
    "x_dimension_mm" / Float64n,
    "y_dimension_mm" / Float64n,
    "z_resolution_um" / Float64n,
    "comp_eff_2" / Float64n,
    "comp_eff_3" / Float64n,
    "noise_thresh" / Float64n,
    "range_adj" / Float64n,
    "base_pos" / Int8un,
)

hw_info_03_header = Struct(
    "model_name" / PaddedString(16, "ascii"),
    "serial_number" / PaddedString(16, "ascii"),
    "spect_sn" / PaddedString(16, "ascii"),
    "rom_ver" / PaddedString(16, "ascii"),
    "unknown" / PaddedString(16, "ascii"),
    "eq_calib_year" / Int16un,
    "eq_calib_month" / Int16un,
    "eq_calib_day" / Int16un,
    "eq_calib_hour" / Int16un,
    "eq_calib_minute" / Int16un,
    "spect_calib_year" / Int16un,
    "spect_calib_month" / Int16un,
    "spect_calib_day" / Int16un,
    "spect_calib_hour" / Int16un,
    "spect_calib_minute" / Int16un,
)

hw_info_02_header = Struct(
    "model_name" / PaddedString(16, "ascii"),
    "serial_number" / PaddedString(16, "ascii"),
    "spect_sn" / PaddedString(16, "ascii"),
    "rom_ver" / PaddedString(16, "ascii"),
    "eq_calib_year" / Int16un,
    "eq_calib_month" / Int16un,
    "eq_calib_day" / Int16un,
    "spect_calib_year" / Int16un,
    "spect_calib_month" / Int16un,
    "spect_calib_day" / Int16un,
)

hw_info_01_header = Struct(
    "model_name" / PaddedString(16, "ascii"),
    "serial_number" / PaddedString(16, "ascii"),
    "spect_sn" / PaddedString(16, "ascii"),
    "rom_ver" / PaddedString(16, "ascii"),
    "eq_calib_year" / Int16un,
    "eq_calib_month" / Int16un,
    "eq_calib_day" / Int16un,
    "spect_calib_year" / Int16un,
    "spect_calib_month" / Int16un,
    "spect_calib_day" / Int16un,
)

patient_info_02_header = Struct(
    "patient_id" / PaddedString(32, "ascii"),
    "first_name" / PaddedString(32, "ascii"),
    "last_name" / PaddedString(32, "ascii"),
    "mid_name" / PaddedString(8, "ascii"),
    "sex" / Int8un,
    "birth_date" / Int16un[3],
    "occup_reg" / Int8un[20][2],
    "r_date" / Int16un[3],
    "record_id" / Int8un[16],
    "lv_date" / Int16un[3],
    # I've not found files that have the below information,
    # so it's difficult to confirm the remaining.
    "physician" / Int8un[64][2],  # [64 2] ???
    "zip_code" / Int8un[12],  # how does this make sense.
    "addr" / Int8un[48][2],  # [48 2]
    "phones" / Int8un[16][2],  # [16 2]
    "nx_date" / Int16un[6],  # [1 6]
    "multipurpose_field" / Int8un[20][3],  # [20 3]
    "descp" / Int8un[64],
    "reserved" / Int8un[32],
)

file_info_header = Struct(
    "0x2" / Int32un,
    "0x3e8" / Int32un,
    "8.0.1.20198" / PaddedString(32, "ascii"),
)

capture_info_02_header = Struct(
    "eye" / Int8un,
    "scan_mode" / Int8un,
    "session_id" / Int32un,
    "label" / PaddedString(100, "ascii"),
    "cap_date" / Int16un[6],
)

capture_info_header = Struct(
    "eye" / Int8un,
    "cap_date" / Int16un[6],
)

img_trc_02_header = Struct(
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "num_slices_0x2" / Int32un,
    "format" / Int8un,
    "size" / Int32un,
)

img_trc_header = Struct(
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "size" / Int32un,
)

# param_obs_02 has been found to be 90 or 6.
# This first struct handles 90, next handles 6.
# The first "0x1" seems to indicate which type
# of header to expect (0: long, 1: short)
param_obs_02_header = Struct(
    "0x1" / Int16un,
    "0xffff" / Int16un[2],
    "camera_model" / PaddedString(12, "ascii"),
    "image_quality" / PaddedString(24, "ascii"),
    "0x300" / Int16un,
    "0x1" / Int16un,
    "0x0" / Int16un,
    "color_temp" / PaddedString(24, "ascii"),
    "0x2014" / Int16un,
    "zeros" / Int8un[12],
)

param_obs_02_short_header = Struct(
    "0x1" / Int16un,
    "0xffff" / Int16un[2],
)
# phMode = fread(fid, 1, 'uint8');
# phAngle = fread(fid, 1, 'uint8');
# phLightLevel = fread(fid, 1, 'uint16');

img_mot_comp_03_header = Struct(
    "0x0" / Int8un,
    "width" / Int32un,
    "height" / Int32un,
    "bits_per_pixel" / Int32un,
    "num_slices" / Int32un,
)

img_mot_comp_02_header = Struct(
    "temp" / Int8un,
    "motion_width" / Int32un,
    "motion_height" / Int32un,
    "motion_depth" / Int32un,
    "motion_number" / Int32un,
    "motion_format" / Int8un,
    "motion_start_x_pos" / Int32un,
    "motion_start_y_pos" / Int32un,
    "motion_end_x_pos" / Int32un,
    "motion_end_y_pos" / Int32un,
    "size" / Int32un,
)

img_mot_comp_header = Struct(
    "motion_width" / Int32un,
    "motion_height" / Int32un,
    "motion_depth" / Int32un,
    "size" / Int32un,
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
    "0x0" / Int8un,
    "unknown" / Int32un[2],
    "bounding_box_in_fundus_pixels" / Int32un[4],
    "version" / PaddedString(32, "ascii"),
    "bounding_box_in_trc_pixels" / Int32un[4],
)

regist_scan_02_header = Struct(
    "clr_scan_region" / Int32un[4],
    "obs_scan_region" / Int32un[4],
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

align_info_header = Struct(
    "unlabeled_1" / Int8un,
    "unlabeled_2" / Int8un,
    "w" / Int32un,
    "n_size" / Int32un,
    "aligndata" / Array(this.w * 2, Int16un),  # if n_size > 0
    # if nblockbytes - (10+n_size) >= 16
    "keyframe_1" / Int32un,
    "keyframe_2" / Int32un,
    "unlabeled_3" / Int32un,
    "unlabeled_4" / Int32un,
)

main_module_info_header = Struct(
    "software_name" / PaddedString(128, "ascii"),
    "file_version_1" / Int16un,
    "file_version_2" / Int16un,
    "file_version_3" / Int16un,
    "file_version_4" / Int16un,
    "string" / PaddedString(128, "ascii"),
)

fast_q2_info_header = Struct("various_quality_statistics" / Float32n[6])

gla_littmann_01_header = Struct("0xffff" / Int32un, "0x1" / Int32un)

thumbnail_header = Struct(
    "size" / Int32un,
    # "img" / Int8un[this.size]
)

patientext_info_header = Struct("unknown" / Int8un[128])
