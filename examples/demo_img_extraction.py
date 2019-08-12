from file_io.img import IMG

filepath = '../sample_files/file.img'
img = IMG(filepath)
oct_volume = img.read_oct_volume()  # returns an OCT volume with additional metadata if available
oct_volume.save('img_testing.avi')  # save volume
