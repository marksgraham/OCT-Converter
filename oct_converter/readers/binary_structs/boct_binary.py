from construct import (
    Array,
    Bytes,
    BytesInteger,
    Computed,
    Float64n,
    Hex,
    Int16un,
    Int32un,
    Lazy,
    PaddedString,
    Seek,
    Struct,
    Tell,
    this,
)


headerField = Struct(
    keylength=Int32un, key=PaddedString(this.keylength, "utf8"), dataLength=Int32un
)

floatField = Struct(
    keylength=Int32un,
    key=PaddedString(this.keylength, "utf8"),
    dataLength=Int32un,
    value=Float64n,
)

intField = Struct(
    keylength=Int32un,
    key=PaddedString(this.keylength, "utf8"),
    dataLength=Int32un,
    value=BytesInteger(this.dataLength, signed=False, swapped=True),
)

lazyIntField = Struct(
    "keylength" / Int32un,
    "key" / PaddedString(this.keylength, "utf8"),
    "dataLength" / Int32un,
    "offset" / Tell,
    "end" / Computed(this.offset + this.dataLength),
    "value" / Lazy(Bytes(this.dataLength)),
    Seek(this.end),
)

date = Struct(
    year=Int16un,
    month=Int16un,
    dow=Int16un,
    day=Int16un,
    hour=Int16un,
    minute=Int16un,
    second=Int16un,
    millisecond=Int16un,
)
dateField = Struct(
    keylength=Int32un,
    key=PaddedString(this.keylength, "utf8"),
    dataLength=Int32un,
    value=date,
)

strField = Struct(
    keylength=Int32un,
    key=PaddedString(this.keylength, "utf8"),
    dataLength=Int32un,
    value=PaddedString(this.dataLength, "utf8"),
)

bioptigen_oct_header_struct = Struct(
            "magicNumber" / Hex(Int32un),
            "version" / Hex(Int16un),
            "frameheader" / headerField,
            "framecount" / intField,
            "linecount" / intField,
            "linelength" / intField,
            "sampleformat" / intField,
            "description" / strField,
            "xmin" / floatField,
            "xmax" / floatField,
            "xcaption" / strField,
            "ymin" / floatField,
            "ymax" / floatField,
            "ycaption" / strField,
            "scantype" / intField,
            "scandepth" / floatField,
            "scanlength" / floatField,
            "azscanlength" / floatField,
            "elscanlength" / floatField,
            "objectdistance" / floatField,
            "scanangle" / floatField,
            "scans" / intField,
            "frames" / intField,
            "dopplerflag" / intField,
            "config" / lazyIntField,
            BytesInteger(4, signed=False, swapped=True),
        )

oct_frame_header_struct = Struct(
            "framedata" / headerField,
            "framedatetime" / dateField,
            "frametimestamp" / floatField,
            "framelines" / intField,
            "keylength" / Int32un,
            "key" / PaddedString(this.keylength, "utf8"),
            "dataLength" / Int32un,
        )

oct_frame_data_struct = Struct(
            "rows" / Computed(this._._.header.linelength.value),
            "columns" / Computed(this._.header.framelines.value),
            "totalpixels" / Computed(this.rows * this.columns),
            "offset" / Tell,
            "end" / Computed(this.offset + this.totalpixels * 2),
            "pixels" / Lazy(Array(this.totalpixels, Int16un)),
            Seek(this.end),
        )
oct_frame_struct = Struct(
            "header" / oct_frame_header_struct,
            "image" / oct_frame_data_struct,
            BytesInteger(4, signed=False, swapped=True),
        )
oct_frame_stack_struct = Array(this.header.framecount.value, oct_frame_struct)

bioptigen_file_structure = Struct(
            "header" / bioptigen_oct_header_struct, "data" / oct_frame_stack_struct
        )