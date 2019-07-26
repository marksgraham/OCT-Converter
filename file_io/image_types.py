class OCTVolumeWithMetaData(object):
    ''' Simple class to hold the OCT volume and any related metadata extracted from the volumes'''

    def __init__(self, volume, laterality=None, patient_id = None, patient_dob=None):
        self.volume = volume
        self.laterality = laterality
        self.patient_id = patient_id
        self.DOB = patient_dob

    def save(self,filepath):
        raise NotImplementedError

class FundusImageWithMetaData(object):
    ''' Simple class to hold the fundus image and any related metadata extracted.'''

    def __init__(self, image, laterality=None, patient_id = None, patient_dob=None):
        self.image = image
        self.laterality = laterality
        self.patient_id = patient_id
        self.DOB = patient_dob

    def save(self,filepath):
        raise NotImplementedError