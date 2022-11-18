from oct_converter.readers import Dicom

filepath = "../sample_files/sample_dcm.dcm"
file = Dicom(filepath)
oct_volume = (
    file.read_oct_volume()
)  # returns an OCT volume with additional metadata if available

oct_volume.save("dcm_testing.avi")
