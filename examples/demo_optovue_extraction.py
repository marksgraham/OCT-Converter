from oct_converter.readers import POCT

filepath = "../sample_files/sample.OCT"
poct = POCT(filepath)
oct_volumes = poct.read_oct_volume()

for volume in oct_volumes:
    volume.peek()  # plots a montage of the volume
print("debug")
