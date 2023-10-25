from oct_converter.dicom import create_dicom_from_oct
from oct_converter.readers import POCT

filepath = "../sample_files/sample.OCT"
poct = POCT(filepath)
oct_volumes = poct.read_oct_volume()

for volume in oct_volumes:
    volume.peek()  # plots a montage of the volume
print("debug")

# create DICOM from .OCT
dcm = create_dicom_from_oct(filepath)
# Output dir can be specified, otherwise will
# default to current working directory.
# If multiple volumes are identified within the file,
# multiple DICOMs will be outputted.
