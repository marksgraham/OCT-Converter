from construct import (
    Array,
    Float32l,
    Int8un,
    Int16un,
    Int32sn,
    Int32un,
    Int64un,
    Float64l,
    PaddedString,
    Struct,
    this,
)

# Mostly based on description of .e2e file format here:
#         https://bitbucket.org/uocte/uocte/wiki/Heidelberg%20File%20Format.

header_structure = Struct(
    "magic1" / PaddedString(12, "ascii"),
    "version" / Int32un,
    "unknown" / Array(10, Int16un),
)
main_directory_structure = Struct(
    "magic2" / PaddedString(12, "ascii"),
    "version" / Int32un,
    "unknown" / Array(10, Int16un),
    "num_entries" / Int32un,
    "current" / Int32un,
    "prev" / Int32un,
    "unknown3" / Int32un,
)
sub_directory_structure = Struct(
    "pos" / Int32un,
    "start" / Int32un,
    "size" / Int32un,
    "unknown" / Int32un,
    # Patient DB ID is set by the software
    # and is not necessarily equal to patient_id_structure's patient_id
    "patient_db_id" / Int32un,
    "study_id" / Int32un,
    "series_id" / Int32un,
    "slice_id" / Int32sn,
    "unknown2" / Int16un,
    "unknown3" / Int16un,
    "type" / Int32un,
    "unknown4" / Int32un,
)
chunk_structure = Struct(
    "magic3" / PaddedString(12, "ascii"),
    "unknown" / Int32un,
    "unknown2" / Int32un,
    "pos" / Int32un,
    "size" / Int32un,
    "unknown3" / Int32un,
    # Patient DB ID is set by the software
    # and is not necessarily equal to patient_id_structure's patient_id
    "patient_db_id" / Int32un,
    "study_id" / Int32un,
    "series_id" / Int32un,
    "slice_id" / Int32sn,
    "ind" / Int16un,
    "unknown4" / Int16un,
    "type" / Int32un,
    "unknown5" / Int32un,
)
image_structure = Struct(
    "size" / Int32un,
    "type" / Int32un,
    "unknown" / Int32un,
    "height" / Int32un,
    "width" / Int32un,
)
patient_id_structure = Struct(
    "first_name" / PaddedString(31, "ascii"),
    "surname" / PaddedString(51, "ascii"),
    "title" / PaddedString(15, "ascii"),
    "birthdate" / Int32un,
    "sex" / PaddedString(1, "ascii"),
    "patient_id" / PaddedString(25, "ascii"),
)
lat_structure = Struct(
    "unknown" / Array(14, Int8un),
    "laterality" / PaddedString(1, "ascii"),
    "unknown2" / Int8un,
)
contour_structure = Struct(
    "unknown0" / Int32un,
    "id" / Int32un,
    "unknown1" / Int32un,
    "width" / Int32un,
)

# following the spec from
# https://github.com/neurodial/LibE2E/blob/d26d2d9db64c5f765c0241ecc22177bb0c440c87/E2E/dataelements/bscanmetadataelement.cpp#L75
bscan_metadata = Struct(
    "unknown1" / Int32un,
    "imgSizeY" / Int32un,
    "imgSizeX" / Int32un,
    "posX1" / Float32l,
    "posY1" / Float32l,
    "posX2" / Float32l,
    "posY2" / Float32l,
    "zero1" / Int32un,
    "unknown2" / Float32l,
    "scaley" / Float32l,
    "unknown3" / Float32l,
    "zero2" / Int32un,
    "unknown4" / Array(2, Float32l),
    "zero3" / Int32un,
    "imgSizeWidth" / Int32un,
    "numImages" / Int32un,
    "aktImage" / Int32un,
    "scanType" / Int32un,
    "centrePosX" / Float32l,
    "centrePosY" / Float32l,
    "unknown5" / Int32un,
    "acquisitionTime" / Int64un,
    "numAve" / Int32un,
    "imgQuality" / Float32l,
)

# Chunk 7: Eye Data (libE2E)
eye_data = Struct(
    "eyeSide" / PaddedString(1, "ascii"),
    "iop_mmHg" / Float64l,
    "refraction_dpt" / Float64l,
    "c_curve_mm" / Float64l,
    "vfieldMean" / Float64l,
    "vfieldVar" / Float64l,
    "cylinder_dpt" / Float64l,
    "axis_deg" / Float64l,
    "correctiveLens" / Int16un,
    "pupilSize_mm" / Float64l,
)

# 9001 Device Name
# Files examined have n_strings=3, string_size=256,
# text=["Heidelberg Retina Angiograph", "HRA", ""]
device_name = Struct(
    "n_strings" / Int32un,
    "string_size" / Int32un,
    "text" / Array(this.n_strings, PaddedString(this.string_size, "u16"))
)

# 9005 Examined Structure
# Files examined have n_strings=1, string_size=256,
# text=["Retina"]
examined_structure = Struct(
    "n_strings" / Int32un,
    "string_size" / Int32un,
    "text" / Array(this.n_strings, PaddedString(this.string_size, "u16"))
)

# 9006 Scan Pattern
# Files examined have n_strings=2, string_size=256,
# and scan patterns including "OCT Art Volume", "Images", "OCT B-SCAN",
# "3D Volume", "OCT Star Scan"
scan_pattern = Struct(
    "n_strings" / Int32un,
    "string_size" / Int32un,
    "text" / Array(this.n_strings, PaddedString(this.string_size, "u16"))
)

# 9007 Enface Modality
# Files examined have n_strings=2, string_size=256,
# and modalities including ["Infra-Red", "IR"],
# ["Fluroescein Angiography", "FA"], ["ICG Angiography", "ICGA"]
enface_modality = Struct(
    "n_strings" / Int32un,
    "string_size" / Int32un,
    "text" / Array(this.n_strings, PaddedString(this.string_size, "u16"))
)

# 9008 OCT Modality
# Files examined have n_strings=2, string_size=256, text=["OCT", "OCT"]
oct_modality = Struct(
    "n_strings" / Int32un,
    "string_size" / Int32un,
    "text" / Array(this.n_strings, PaddedString(this.string_size, "u16"))
)

# 10025 Localizer
# From eyepy; "transform" is described as "Parameters of affine transformation"
localizer = Struct(
    "unknown" / Array(6, Float32l),
    "windate" / Int32un,
    "transform" / Array(6, Float32l),
)

# 3 seems to indicate the start of the chunk pattern
# Examined files seem to have a mostly-regular pattern of 3, 2, ..., 5, 39
# Both chunks 3 and 5 seem to include laterality info
pre_data = Struct(
    "unknown" / Int32un,
    "laterality" / PaddedString(1, "ascii"),
    # There's more here that I'm unsure of.
    # There seems to be an "ART" in this chunk.
)

# 39 has some time zone data
time_data = Struct(
    "unknown" / Array(46, Int32un),
    "timezone1" / PaddedString(66, "u16"),
    "unknown2" / Array (9, Int16un),
    "timezone2" / PaddedString(66, "u16"),
    # There's more in this chunk (possibly datetimes, given tz)
    # and the chunk size varies.
)

# 52, 54, 1000, 1001 seem to be UIDs with padded strings
# 1000 may be StudyInstanceUID
uid_data = Struct(
    "uid" / PaddedString(64,"ascii")
)

# 1007 padded string with a brand name
unknown_data = Struct(
    "unknown" / PaddedString(64,"ascii")
)
