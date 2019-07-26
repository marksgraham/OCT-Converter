from file_io.file_readers import Dicom


filepath = '/home/mark/Downloads/0077_Test_DICOMPatient__245_Grid_OD_2017-11-02_15-39-49_M_1977-02-04_Main Report_Stack001_20190515183143693.dcm'
file = Dicom(filepath)
oct_volumes  = file.read_oct_volume() # returns an OCT volume with additional metadata if available

#for volume in oct_volumes:
#    volume.save(f'{volume.patient_id}.avi')


