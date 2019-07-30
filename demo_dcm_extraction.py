from file_io.dcm import Dicom


filepath = 'sample_dcm.dcm'
file = Dicom(filepath)
oct_volumes  = file.read_oct_volume() # returns an OCT volume with additional metadata if available

#for volume in oct_volumes:
#    volume.save(f'{volume.patient_id}.avi')


