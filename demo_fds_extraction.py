from file_io.fds import FDS

filepath = 'sample_files/file.fds'
fds = FDS(filepath)
oct_volume = fds.read_oct_volume() # returns an OCT volume with additional metadata if available
 #oct_volume.save('fds_testing.avi') # save volume

fundus_image = fds.read_fundus_image()# returns a theia-like FundusImage with additional metadata if available
#fundus_image.save()


