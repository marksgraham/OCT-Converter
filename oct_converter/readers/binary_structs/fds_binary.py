from construct import Array, Float64n, Int32un, PaddedString, Struct

header = Struct(
    "FOCT" / PaddedString(4, "ascii"),
    "FDA" / PaddedString(3, "ascii"),
    "version_info_1" / Int32un,
    "version_info_2" / Int32un,
)
oct_header = Struct(
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
    "unknown" / PaddedString(1, "ascii"),
    "size" / Int32un,
)

# ref: https://github.com/neurodial/LibOctData/blob/master/octdata/import/topcon/topconread.cpp#L318
param_scan_04_header = Struct(
    "unknown" / Array(3, Int32un),
    "x_dimension_mm" / Float64n,
    "y_dimension_mm" / Float64n,
    "z_resolution_um" / Float64n,
)
