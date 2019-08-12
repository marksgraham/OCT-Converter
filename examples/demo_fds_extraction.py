from file_io.fds import FDS

filepath = '../sample_files/file.fds'
fds = FDS(filepath)
oct_volume = fds.read_oct_volume()  # returns an OCT volume with additional metadata if available
oct_volume.save('fds_testing.avi')  # save volume as a movie
oct_volume.save('fds_testing.png')  # save volume as a set of sequential images, fds_testing_[1...N].png

fundus_image = fds.read_fundus_image()  # returns a  Fundus image with additional metadata if available
fundus_image.save('fds_testing_fundus.jpg')
