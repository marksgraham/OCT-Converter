from construct import (
    Array,
    Float32l,
    Int8un,
    Int16un,
    Int32sn,
    Int32un,
    Int64un,
    PaddedString,
    Struct,
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
    "patient_id" / Int32un,
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
    "patient_id" / Int32un,
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
    "width" / Int32un,
    "height" / Int32un,
)
patient_id_structure = Struct(
    "first_name" / PaddedString(31, "ascii"),
    "surname" / PaddedString(66, "ascii"),
    "birthdate" / Int32un,
    "sex" / PaddedString(1, "ascii"),
    "patient_id" / PaddedString(25, "ascii"),
)
lat_structure = Struct(
    "unknown" / Array(14, Int8un), "laterality" / Int8un, "unknown2" / Int8un
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
    "imgSizeX" / Int32un,
    "imgSizeY" / Int32un,
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
