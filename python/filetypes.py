import struct
import numpy as np
''' Class for extractig data from topcon .fds file format. Mostly based on description of file format here:
 https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format'''

class FDS(object):
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
        [print(key) for key in chunk_dict.keys()]
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
            raw_volume = [struct.unpack('H', f.read(2)) for pixel in range(number_pixels)]
            volume = np.array(raw_volume)
            volume = volume.reshape(width,height,number_slices,order='F')
            volume = np.transpose(volume,[1,0,2])
        return volume

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
            image_copy = image.copy()
            image[:,:,0] = image_copy[:,:,2]
            image[:,:,2] = image_copy[:,:,0]
        return image

