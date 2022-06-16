from oct_converter.readers import POCT

filepath = "/Users/mark/Dropbox/Work/Projects/OCT-Converter/my_example_volumes/optovue-oct/aaa_111111_Retina Map_OD_2022-05-31_09.31.11_1.OCT"
poct = POCT(filepath)
oct_volumes = poct.read_oct_volume()

for volume in oct_volumes:
    volume.peek()  # plots a montage of the volume
print("debug")
