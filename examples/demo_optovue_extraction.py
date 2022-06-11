from oct_converter.readers import IMG

filepath = "../sample_files/file.img"
img = IMG(filepath)
oct_volume = (
    img.read_oct_volume()
)  # returns an OCT volume with additional metadata if available
oct_volume.peek()  # plots a montage of the volume
oct_volume.save("img_testing.avi")  # save volume
