import numpy as np
from construct import (Struct, Int16un, Int32un, PaddedString, Float64n, 
                        BytesInteger, Tell, Computed, Seek, Hex, Lazy, 
                        Array,this,Bytes)
# from oct_converter.image_types import OCTVolumeWithMetaData, FundusImageWithMetaData
from oct import OCTVolumeWithMetaData
from pathlib import Path
import h5py, tempfile
                            
headerField = Struct(keylength=Int32un,
                     key=PaddedString(this.keylength, "utf8"), 
                     dataLength=Int32un)

floatField = Struct(keylength=Int32un,
                    key=PaddedString(this.keylength, "utf8"), 
                    dataLength=Int32un, 
                    value=Float64n)

intField = Struct(keylength=Int32un,
                  key=PaddedString(this.keylength, "utf8"), 
                  dataLength=Int32un, 
                  value=BytesInteger(this.dataLength,
                                     signed=False,
                                     swapped=True
                                     )
                  )

lazyIntField = Struct("keylength"/Int32un,
                        "key"/PaddedString(this.keylength, "utf8"), 
                        "dataLength"/Int32un, 
                        "offset"/Tell, 
                        "end"/ Computed(this.offset + this.dataLength),
                        "value" / Lazy(Bytes(this.dataLength)),
                        Seek(this.end)
            )

date = Struct(year=Int16un,month=Int16un,dow=Int16un,day=Int16un,hour=Int16un,minute=Int16un,second=Int16un,millisecond=Int16un)
dateField = Struct(keylength=Int32un,key=PaddedString(this.keylength, "utf8"), dataLength=Int32un, value=date)

strField = Struct(keylength=Int32un,key=PaddedString(this.keylength, "utf8"), dataLength=Int32un, value=PaddedString(this.dataLength, "utf8"))

class BOCT(object):
    """ Class for extracting data from Bioptigen's .OCT file format.

        Attributes:
            filepath (str): Path to .img file for reading.
            header_structure (obj:Struct): Defines structure of volume's header.
            main_directory_structure (obj:Struct): Defines structure of volume's main directory.
            sub_directory_structure (obj:Struct): Defines structure of each sub directory in the volume.
            chunk_structure (obj:Struct): Defines structure of each data chunk.
            image_structure (obj:Struct): Defines structure of image header.
    """

    bioptigen_scan_type_map = {0:'linear',
                                1:'rect',
                                3:'rad'}

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(self.filepath)
        self.oct_header = Struct(
                                "magicNumber" / Hex(Int32un),
                                "version" / Hex(Int16un),
                                "frameheader"/headerField,
                                "framecount"/ intField,
                                "linecount" / intField,
                                "linelength" / intField,
                                "sampleformat" / intField,
                                "description" / strField,
                                "xmin" / floatField,
                                "xmax" / floatField,
                                "xcaption" / strField,
                                "ymin" / floatField,
                                "ymax" / floatField,
                                "ycaption" / strField,
                                "scantype" / intField,
                                "scandepth" / floatField,
                                "scanlength" / floatField,
                                "azscanlength" / floatField,
                                "elscanlength" / floatField,
                                "objectdistance" / floatField,
                                "scanangle" / floatField,
                                "scans" / intField,
                                "frames" / intField,
                                "dopplerflag" / intField,
                                "config" / lazyIntField,
                                BytesInteger(4,signed=False,swapped=True)
                            )
        self.frame_header = Struct(
            "framedata" / headerField,
            "framedatetime" / dateField,
            "frametimestamp" / floatField,
            "framelines" / intField,
            "keylength"/Int32un,
            "key"/PaddedString(this.keylength, "utf8"), 
            "dataLength"/Int32un
            )

        self.frame_image = Struct(
            'rows' / Computed(this._._.header.linelength.value),
            'columns'/ Computed(this._.header.framelines.value),
            'totalpixels'/ Computed(this.rows*this.columns),
            'offset' / Tell,
            'end'/ Computed(this.offset + this.totalpixels*2),
            'pixels' / Lazy(Array(this.totalpixels,Int16un)),
            Seek(this.end)
            )

        self.frame = Struct(
            "header"/self.frame_header,
            "image" /self.frame_image,
            BytesInteger(4,signed=False,swapped=True)
            )
        
        self.frame_stack = Array(this.header.framecount.value, self.frame)
        self.file_structure = Struct(
                                "header" / self.oct_header,
                                "data" / self.frame_stack
                                )
    def read_oct_volume(self):
        """ Reads OCT data.

            Returns:
                obj:OCTVolumeWithMetaData
        """
        oct = self.file_structure.parse_file(self.filepath)
        self.header = oct.header
        self.frames = FrameGenerator(oct.data)
        self.scantype = self.bioptigen_scan_type_map[self.header.scantype.value]
        ##Values expected from header
        self.framecount = self.header.frames.value
        self.scancount = self.header.scans.value
        self.totalframes = self.header.framecount.value
        
        ##values obtained from data
        self.Bscan_geom = self.frames.geom
        self.original_xbounds = (self.header.xmin.value,self.header.xmax.value)
        self.original_ybounds = (self.header.ymin.value,self.header.ymax.value)
        self.original_extent = (self.original_ybounds,self.original_xbounds) ##For plotting

        self.xresolution =  self.header.scandepth.value/self.Bscan_geom[1]
        self.yresolution =  self.header.scanlength.value/self.Bscan_geom[0]
        self.zresolution = self.header.elscanlength.value/self.scancount
        self.zextent = (self.original_ybounds[0],self.original_ybounds[1],0,self.header.elscanlength.value)
        ##Bioptigen OCTs compress 4D volume to 3D 
        ##2D images of [x,y], either scans or frames (repeats over time), stacked 
        self.oct_shape = (self.frames.geom[0],     ##x,y,z+t
                          self.frames.geom[1],
                          self.frames.count)

        self.vdim3 = int(self.totalframes/self.framecount)
        self.vdim4 = int(self.framecount)
        self.vol_frames_shape = (self.vdim4,self.vdim3)
        self.volume_shape = (self.vdim4,
                            self.vdim3,
                            self.frames.geom[0],
                            self.frames.geom[1]     ##t,z,x,y                            
                            )
        ##Index conversion between framestack (3D) and volume (3D+Time)
        stack_to_vol = np.asarray([i+j*(self.vdim4) for i in range(0,self.vdim4) for j in range(0,self.vdim3)])
        vol_to_stack = np.asarray([i+j*(self.vdim3) for i in range(0,self.vdim3) for j in range(0,self.vdim4)])
        self.indicies = {'to_vol':stack_to_vol,
                        'to_stack':vol_to_stack}
        self._stack_ind_to_sf = [(s,f) for s in range(0,self.vdim3) for f in range(0,self.vdim4)]
        self.loaded = False
        self._create_disk_buffer()
    
    def _create_disk_buffer(self,name='vol'):
        _,_,x,y = self.volume_shape
        chunksize = (1,1,x,y)
        tf = h5py.File(tempfile.TemporaryFile(), "w")
        buffer = tf.create_dataset(name, 
                                    shape=self.volume_shape, 
                                    dtype = np.uint16,
                                    chunks=chunksize)
        setattr(self,name,buffer)

    def load_oct_volume(self):
        volFrames = np.reshape(self.frames.data,self.vol_frames_shape)
        try:
            with open(self.filepath, 'rb') as f:
                for t,v in enumerate(volFrames):
                    for z,frame in enumerate(v):
                        self.vol[t,z,:,:] = frame.load(f,self.Bscan_geom)
            self.loaded=True
        except Exception as e:
            print(e)
            print('Stopping load')
        return OCTVolumeWithMetaData(self.vol)

    def read_fundus_image(self):
        pass

class OCTFrame:
    def __init__(self,frame):
        self.frame = frame
        self.count = self.frame.image.totalpixels
        self.abs_pos = self.frame.image.offset

    def from_bytes(self,f):
        f.seek(self.abs_pos,0)
        im = np.fromfile(f, dtype=np.uint16, count=self.count)
        return im

    def load(self,f,imsize):
        return np.resize(self.from_bytes(f),imsize)

    def __lt__(self,other):
        pass
    def __eq__(self,other):
        return self.im == other


class FrameGenerator:
    def __init__(self,oct_data):
        self.data = None
        self.last = 0
        self.xres = 1
        self.yres = 1
        self.oct_data = oct_data

        frame0 = oct_data[0]
        self.Ascans = frame0.image.columns
        self.depth = frame0.image.rows
        self.geom = (self.Ascans, self.depth)
        self._get_frames()
        
    def _get_frames(self):
        self.data = np.asarray([OCTFrame(frame) for frame in self.oct_data])
        self.count = len(self.data)
        self._to_original_order = np.asarray(range(self.count))
        self._to_current_order = []

    def set_frameorder(self,indexArr):
        self.data = self._reorder_frames(indexArr)
        self._to_current_order.append(indexArr)
        self._to_original_order = self._to_original_order[indexArr]

    def _reorder_frames(self,indexArr):
        try:
            return self.data[indexArr]
        except Exception as e:
            print(e)

    def get_original_frame_order(self):
        return self._reorder_frames(self._to_original_order)

    def set_original_frame_order(self):
        self.set_frameorder(self._to_original_order)
        self._to_original_order = np.asarray(range(self.count))
        self._to_current_order = []

    def set_scale(self,xres = 1, yres = 1):
        self.xres = xres
        self.yres = yres