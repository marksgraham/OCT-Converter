from oct_converter.dicom import create_dicom_from_oct
from oct_converter.readers import BOCT

filepath = "../sample_files/sample.OCT"
boct = BOCT(filepath)
oct_volumes = boct.read_oct_volume(
    diskbuffered=True
)  # returns an OCT volume with additional metadata if available
for oct in oct_volumes:
    oct.peek()  # plots a montage of the volume
    oct.save("boct_testing.avi")  # save volume as a movie
    oct.save(
        "boct_testing.png"
    )  # save volume as a set of sequential images, fds_testing_[1...N].png

# create DICOM from .OCT
dcm = create_dicom_from_oct(filepath)
# Output dir can be specified, otherwise will
# default to current working directory.
# If multiple volumes are identified within the file,
# multiple DICOMs will be outputted.
# Additionally, diskbuffered can be specified to store
# volume on disk using HDF5 to reduce memory usage
dcm = create_dicom_from_oct(filepath, diskbuffered=True)
