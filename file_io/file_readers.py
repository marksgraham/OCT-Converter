import struct
import numpy as np
from construct import PaddedString, Int16un, Struct, Int32sn, Int32un, Array
from file_io.image_types import OCTVolumeWithMetaData, FundusImageWithMetaData

class FDS(object):
    ''' Class for extracting data from Topcon's .fds file format. Mostly based on description of file format here:
     https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format'''
    def __init__(self,filepath):
        self.filepath = filepath
        self.chunk_dict = self.get_list_of_file_chunks()


    def get_list_of_file_chunks(self):
        chunk_dict = {}
        with open(self.filepath,'rb') as f:
            # skip header
            f.read(4) # "FOCT"
            f.read(3) # "FDA"
            struct.unpack('i', f.read(4)) # version info
            struct.unpack('i', f.read(4)) # version info
            eof = False
            while not eof:
                chunk_name_size = struct.unpack('b',f.read(1))[0]
                if chunk_name_size == 0:
                    eof = True
                else:
                    chunk_name = f.read(chunk_name_size)
                    chunk_size = struct.unpack('i',f.read(4))[0]
                    chunk_location = f.tell()
                    f.seek(chunk_size,1)
                    chunk_dict[chunk_name] = [chunk_location, chunk_size]
        print('File {} contains the following chunks:'.format(self.filepath))
        for key in chunk_dict.keys():
            print(key)
        return chunk_dict

    def read_oct_volume(self):
        if b'@IMG_SCAN_03' not in self.chunk_dict:
            raise ValueError('Could not find OCT header @IMG_SCAN_03 in chunk list')
        with open(self.filepath, 'rb') as f:
            chunk_location, chunk_size = self.chunk_dict[b'@IMG_SCAN_03']
            f.seek(chunk_location)
            f.seek(1,1) # byte to skip
            width= struct.unpack('i', f.read(4))[0]
            height= struct.unpack('i', f.read(4))[0]
            bits_per_pixel = struct.unpack('i', f.read(4))[0]
            number_slices = struct.unpack('i', f.read(4))[0]
            f.seek(1,1) # byte to skip
            size = struct.unpack('i', f.read(4))[0]
            number_pixels = width * height * number_slices
            raw_volume = np.fromstring(f.read(number_pixels*2), dtype=np.uint16)
            volume = np.array(raw_volume)
            volume = volume.reshape(width,height,number_slices,order='F')
            volume = np.transpose(volume,[1,0,2])
        oct_volume = OCTVolumeWithMetaData([volume[:, :, i] for i in range(volume.shape[2])])
        return oct_volume

    def read_fundus_image(self):
        if b'@IMG_OBS' not in self.chunk_dict:
            raise ValueError('Could not find OCT header @IMG_OBS in chunk list')
        with open(self.filepath, 'rb') as f:
            chunk_location, chunk_size = self.chunk_dict[b'@IMG_OBS']
            f.seek(chunk_location)
            width= struct.unpack('i', f.read(4))[0]
            height= struct.unpack('i', f.read(4))[0]
            bits_per_pixel = struct.unpack('i', f.read(4))[0]
            number_slices = struct.unpack('i', f.read(4))[0]
            f.seek(1,1) # byte to skip
            size = struct.unpack('i', f.read(4))[0]
            number_pixels = width * height * number_slices
            raw_image = [struct.unpack('B', f.read(1)) for pixel in range(size)]
            image = np.array(raw_image)
            image = image.reshape(3,width,height,order='F')
            image = np.transpose(image,[2,1,0])
            #image_copy = image.copy()
            #image[:,:,0] = image_copy[:,:,2]
            #image[:,:,2] = image_copy[:,:,0]
            image = image.astype(np.float32)
        fundus_image = FundusImageWithMetaData(image)
        return fundus_image

class E2E(object):
    ''' Class for extracting data from heidelberg's .e2e file format. Mostly based on description of file format here:
         https://bitbucket.org/uocte/uocte/wiki/Heidelberg%20File%20Format'''
    def __init__(self,filepath):
        self.filepath = filepath

        # header
        self.header_structure = Struct(
            'magic' / PaddedString(12, 'ascii'),
            'version' / Int32un,
            'unknown' / Array(10, Int16un)
        )
        # main directory
        self.main_directory_structure = Struct(
            'magic' / PaddedString(12, 'ascii'),
            'version' / Int32un,
            'unknown' / Array(10, Int16un),
            'num_entries' / Int32un,
            'current' / Int32un,
            'prev' / Int32un,
            'unknown3' / Int32un,
        )
        # data chunks
        self.sun_directory_structure = Struct(
            'pos' / Int32un,
            'start' / Int32un,
            'size' / Int32un,
            'unknown' / Int32un,
            'patient_id' / Int32un,
            'study_id' / Int32un,
            'series_id' / Int32un,
            'slice_id' / Int32sn,
            'unknown2' / Int16un,
            'unknown3' / Int16un,
            'type' / Int32un,
            'unknown4' / Int32un,
        )

        self.chunk_structure = Struct(
            'magic' / PaddedString(12, 'ascii'),
            'unknown' / Int32un,
            'unknown2' / Int32un,
            'pos' / Int32un,
            'size' / Int32un,
            'unknown3' / Int32un,
            'patient_id' / Int32un,
            'study_id' / Int32un,
            'series_id' / Int32un,
            'slice_id' / Int32sn,
            'ind' / Int16un,
            'unknown4' / Int16un,
            'type' / Int32un,
            'unknown5' / Int32un,
        )

        self.image_structure = Struct(
            'size' / Int32un,
            'type' / Int32un,
            'unknown' / Int32un,
            'width' / Int32un,
            'height' / Int32un,
        )



    def read_oct_volume(self):
        with open(self.filepath, 'rb') as f:
            raw = f.read(36)
            header = self.header_structure.parse(raw)

            raw = f.read(52)
            main_directory = self.main_directory_structure.parse(raw)

            # traverse list of main directories in first pass
            directory_stack = []

            current = main_directory.current
            while current != 0:
                directory_stack.append(current)
                f.seek(current)
                raw = f.read(52)
                directory_chunk = self.main_directory_structure.parse(raw)
                current = directory_chunk.prev


            # traverse in second pass and  get all subdirectories
            chunk_stack = []
            volume_dict = {}
            for position in directory_stack:
                f.seek(position)
                raw = f.read(52)
                directory_chunk = self.main_directory_structure.parse(raw)

                for ii in range(directory_chunk.num_entries):
                    raw = f.read(44)
                    chunk = self.sun_directory_structure.parse(raw)
                    volume_string = f'{chunk.patient_id}_{chunk.study_id}_{chunk.series_id}'
                    if volume_string not in volume_dict.keys():
                        volume_dict[volume_string] =  chunk.slice_id/2
                    elif chunk.slice_id/2 > volume_dict[volume_string]:
                        volume_dict[volume_string] = chunk.slice_id / 2

                    if chunk.start > chunk.pos:
                        chunk_stack.append([chunk.start,chunk.size])



            # initalise dict to hold all the image volumes
            volume_array_dict = {}
            for volume, num_slices in volume_dict.items():
                if num_slices > 0:
                    volume_array_dict[volume] = [0] * int(num_slices)

            # traverse all chunks and extract slices
            for start, pos in chunk_stack:
                f.seek(start)
                raw = f.read(60)
                chunk = self.chunk_structure.parse(raw)

                if chunk.type == 1073741824: # image data
                    raw = f.read(20)
                    image_data = self.image_structure.parse(raw)

                    if chunk.ind == 0: # fundus data
                        pass
                        # raw_volume = [struct.unpack('H', f.read(2))[0] for pixel in range(height*width)]
                        # image = np.array(raw_volume).reshape(height,width)
                        # plt.imshow(image)
                    elif chunk.ind == 1: # oct data
                        all_bits = [f.read(2) for i in range(image_data.height * image_data.width)]
                        raw_volume = list(map(self.read_custom_float, all_bits))
                        image = np.array(raw_volume).reshape(image_data.width, image_data.height)
                        image = 256* pow(image,1.0/2.4)
                        volume_string = f'{chunk.patient_id}_{chunk.study_id}_{chunk.series_id}'
                        volume_array_dict[volume_string][int(chunk.slice_id/2)-1] = image

            oct_volumes = []
            for key, volume in volume_array_dict.items():
                oct_volumes.append(OCTVolumeWithMetaData(volume=volume, patient_id=key))


        return oct_volumes

    def read_custom_float(self,bytes):
        power = pow(2, 10)
        # convert two bytes to 16-bit binary representation
        bits = bin(bytes[0])[2:].zfill(8)[::-1] + bin(bytes[1])[2:].zfill(8)[::-1]

        # get mantissa and exponent
        mantissa = bits[:10]
        exponent = bits[10:]

        # convert to decimal representations
        mantissa_sum = 1 + int(mantissa, 2) / power
        exponent_sum = int(exponent[::-1], 2) - 63
        decimal_value = mantissa_sum * pow(2, exponent_sum)
        return decimal_value



class Dicom(object):
    def __init__(self,filepath):
        self.filepath = filepath


    def read_oct_volume(self):
        import pydicom
        dicom_data = pydicom.dcmread(self.filepath)
        pixel_data = dicom_data.pixel_array
        oct_volume = OCTVolumeWithMetaData(volume=pixel_data)
        return oct_volume


        print('debug')

