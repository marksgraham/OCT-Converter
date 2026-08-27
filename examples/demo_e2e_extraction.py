import json

from oct_converter.dicom import create_dicom_from_oct
from oct_converter.readers import E2E

filepath = "../sample_files/sample.E2E"
file = E2E(filepath)
oct_volumes = (
    file.read_oct_volume()
)  # returns a list of all OCT volumes with additional metadata if available
for volume in oct_volumes:
    volume.peek(show_contours=True)  # plots a montage of the volume
    volume.save("{}_{}.avi".format(volume.volume_id, volume.laterality))

fundus_images = (
    file.read_fundus_image()
)  # returns a list of all fundus images with additional metadata if available
for image in fundus_images:
    image.save("{}+{}.png".format(image.image_id, image.laterality))

# extract all other metadata
metadata = file.read_all_metadata()
with open("metadata.json", "w") as outfile:
    outfile.write(json.dumps(metadata, indent=4))

# create DICOM(s) from E2E
# Writes, per volume / fundus image found in the file:
#   {stem}_oct_{n}.dcm    - OPT volume
#   {stem}_fundus_{n}.dcm - fundus / enface (if present)
#   {stem}_seg_{n}.dcm    - Height Map Segmentation when layer contours exist
# See demo_e2e_heightmap_seg.py for SEG details and inspection.
dcm = create_dicom_from_oct(filepath)
# Output dir can be specified, otherwise will
# default to current working directory.
# If multiple volumes are present in the E2E file,
# multiple files will be created.
