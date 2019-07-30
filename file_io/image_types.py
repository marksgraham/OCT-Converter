import os
import imageio
import cv2

VIDEO_TYPES = ['.avi','.mp4',]
IMAGE_TYPES = ['.png', '.bmp', '.tiff','.jpg', '.jpeg']


class OCTVolumeWithMetaData(object):
    ''' Simple class to hold the OCT volume and any related metadata extracted from the volumes'''

    def __init__(self, volume, laterality=None, patient_id = None, patient_dob=None):
        self.volume = volume
        self.laterality = laterality
        self.patient_id = patient_id
        self.DOB = patient_dob

    def save(self,filepath):
        extension = os.path.splitext(filepath)[1]
        if extension.lower() in VIDEO_TYPES:
            video_writer = imageio.get_writer(filepath,macro_block_size=None)
            for slice in self.volume:
                video_writer.append_data(slice)
            video_writer.close()
        elif extension.lower() in IMAGE_TYPES:
            base = os.path.splitext(os.path.basename(filepath))[0]
            print('Saving OCT as sequential slices {}_[1..{}]{}'.format(base,len(self.volume),extension))
            full_base = os.path.splitext(filepath)[0]
            for index, slice in enumerate(self.volume):
                filename = '{}_{}{}'.format(full_base,index,extension)
                cv2.imwrite(filename,slice)
        else:
            raise NotImplementedError('Saving with file extension {} not supported'.format(extension))


class FundusImageWithMetaData(object):
    ''' Simple class to hold the fundus image and any related metadata extracted.'''

    def __init__(self, image, laterality=None, patient_id = None, patient_dob=None):
        self.image = image
        self.laterality = laterality
        self.patient_id = patient_id
        self.DOB = patient_dob

    def save(self,filepath):
        extension = os.path.splitext(filepath)[1]
        if extension.lower() in IMAGE_TYPES:
            cv2.imwrite(filepath, self.image)
        else:
            raise NotImplementedError('Saving with file extension {} not supported'.format(extension))