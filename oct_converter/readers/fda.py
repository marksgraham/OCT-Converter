from construct import PaddedString,  Struct,  Int32un
import numpy as np
from oct_converter.image_types import OCTVolumeWithMetaData, FundusImageWithMetaData
from pylibjpeg import decode

class FDA(object):
    """ Class for extracting data from Topcon's .fda file format.

        Notes:
            Mostly based on description of .fda file format here:
            https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format

        Attributes:
            filepath (str): Path to .img file for reading.
            header (obj:Struct): Defines structure of volume's header.
            fundus_header (obj:Struct): Defines structure of fundus header.
            chunk_dict (dict): Name of data chunks present in the file, and their start locations.
    """
    def __init__(self, filepath):
        self.filepath = filepath
        self.header = Struct(
            'FOCT' / PaddedString(4, 'ascii'),
            'FDA' / PaddedString(3, 'ascii'),
            'version_info_1' / Int32un,
            'version_info_2' / Int32un
        )

        self.fundus_header = Struct(
            'width' / Int32un,
            'height' / Int32un,
            'bits_per_pixel' / Int32un,
            'number_slices' / Int32un,
            'unknown' / PaddedString(4, 'ascii'),
            'size' / Int32un,
            # 'img' / Int8un,
        )

        self.chunk_dict = self.get_list_of_file_chunks()


    def get_list_of_file_chunks(self):
        """Find all data chunks present in the file.

        Returns:
            dict
        """
        chunk_dict = {}
        with open(self.filepath, 'rb') as f:
            # skip header
            raw = f.read(15)
            header = self.header.parse(raw)

            eof = False
            while not eof:
                chunk_name_size = np.fromstring(f.read(1), dtype=np.uint8)[0]
                if chunk_name_size == 0:
                    eof = True
                else:
                    chunk_name = f.read(chunk_name_size)
                    chunk_size = np.fromstring(f.read(4), dtype=np.uint32)[0]
                    chunk_location = f.tell()
                    f.seek(chunk_size, 1)
                    chunk_dict[chunk_name] = [chunk_location, chunk_size]
        print('File {} contains the following chunks:'.format(self.filepath))
        for key in chunk_dict.keys():
            print(key)
        return chunk_dict

    def read_fundus_image(self):
        """ Reads fundus image.

            Returns:
                obj:FundusImageWithMetaData
        """
        if b'@IMG_FUNDUS' not in self.chunk_dict:
            raise ValueError('Could not find fundus header @IMG_FUNDUS in chunk list')
        with open(self.filepath, 'rb') as f:
            chunk_location, chunk_size = self.chunk_dict[b'@IMG_FUNDUS']
            f.seek(chunk_location)# Set the chunk’s current position.
            raw = f.read(24)# skip 24 is important
            fundus_header = self.fundus_header.parse(raw)
            number_pixels = fundus_header.width * fundus_header.height * 3
            raw_image = f.read(fundus_header.size)
            image = decode(raw_image)
        fundus_image = FundusImageWithMetaData(image)
        return fundus_image
