from oct_converter.dicom import create_dicom_from_oct
from oct_converter.readers import IMG

filepath = "../sample_files/file.img"
img = IMG(filepath)
oct_volume = (
    img.read_oct_volume()
)  # returns an OCT volume with additional metadata if available
oct_volume.peek()  # plots a montage of the volume
oct_volume.save("img_testing.avi")  # save volume

# create a DICOM from .img
dcm = create_dicom_from_oct(filepath)
# Output dir can be specified, otherwise will
# default to current working directory.
# Additionally, rows, columns, and interlaced can
# be specified to more accurately create an image.
dcm = create_dicom_from_oct(filepath, interlaced=True)
