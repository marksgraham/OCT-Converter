import json

from oct_converter.readers import FDA

# a sample .fda file can be downloaded from the Biobank resource here:
# https://biobank.ndph.ox.ac.uk/showcase/refer.cgi?id=31
filepath = "/Users/mark/Downloads/eg_oct_fda.fda"
fda = FDA(filepath)

oct_volume = (
    fda.read_oct_volume()
)  # returns an OCT volume with additional metadata if available
oct_volume.peek()  # plots a montage of the volume
oct_volume.save("fda_testing.avi")  # save volume as a movie
oct_volume.save(
    "fda_testing.png"
)  # save volume as a set of sequential images, fds_testing_[1...N].png

fundus_image = (
    fda.read_fundus_image()
)  # returns a  Fundus image with additional metadata if available
fundus_image.save("fda_testing_fundus.jpg")

fundus_grayscale_image = fda.read_fundus_image_gray_scale()
if fundus_grayscale_image:
    fundus_grayscale_image.save("fda_testing_grayscalefundus.jpg")

# Read segmentation (contours)
segmentation = fda.read_segmentation()

# extract all other metadata
output_json = dict()
for key in fda.chunk_dict.keys():
    if key in [b"@IMG_JPEG", b"@IMG_FUNDUS", b"@IMG_TRC_02", b"@CONTOUR_INFO"]:
        # these chunks are image chunks and extracted with previous methods
        continue
    json_key = key.decode().split("@")[-1].lower()
    try:
        output_json[json_key] = fda.read_any_info_and_make_dict(key)
    except KeyError:
        print(f"{key} there is no method for getting info from this chunk.")
with open("fda_metadata.json", "w") as outfile:
    outfile.write(json.dumps(output_json, indent=4))
