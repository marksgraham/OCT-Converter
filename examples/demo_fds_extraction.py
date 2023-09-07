import json

from oct_converter.dicom import create_dicom_from_oct
from oct_converter.readers import FDS

# An example .fds file can be downloaded from the Biobank website:
# https://biobank.ndph.ox.ac.uk/showcase/refer.cgi?id=30
filepath = "/home/mark/Downloads/eg_oct_fds.fds"
fds = FDS(filepath)

oct_volume = (
    fds.read_oct_volume()
)  # returns an OCT volume with additional metadata if available
oct_volume.peek()  # plots a montage of the volume
oct_volume.save("fds_testing.avi")  # save volume as a movie
oct_volume.save(
    "fds_testing.png"
)  # save volume as a set of sequential images, fds_testing_[1...N].png
oct_volume.save_projection("projection.png")

fundus_image = (
    fds.read_fundus_image()
)  # returns a  Fundus image with additional metadata if available
fundus_image.save("fds_testing_fundus.jpg")

# extract all other metadata
metadata = fds.read_all_metadata(verbose=True)
with open("fds_metadata.json", "w") as outfile:
    outfile.write(json.dumps(metadata, indent=4))

# create a DICOM from FDS
dcm = create_dicom_from_oct(filepath)
# Output dir can be specified, otherwise will
# default to current working directory.
# Output filename can be specified, otherwise
# will default to the input filename.
