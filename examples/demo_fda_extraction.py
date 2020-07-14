from oct_converter.readers import FDA

filepath = '../../../../13812.fda'
fda = FDA(filepath)
# oct_volume = fds.read_oct_volume()  # returns an OCT volume with additional metadata if available
# oct_volume.peek() # plots a montage of the volume
# oct_volume.save('fds_testing.avi')  # save volume as a movie
# oct_volume.save('fds_testing.png')  # save volume as a set of sequential images, fds_testing_[1...N].png

fundus_image = fda.read_fundus_image()  # returns a  Fundus image with additional metadata if available
fundus_image.save('fds_testing_fundus.jpg')
