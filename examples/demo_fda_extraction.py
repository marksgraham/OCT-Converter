from oct_converter.readers import FDA

# a sample .fda file can be downloaded from the Biobank resource here:
# https://biobank.ndph.ox.ac.uk/showcase/refer.cgi?id=31
filepath = "/Users/mark/Downloads/eg_oct_fda.fda"
fda = FDA(filepath)

oct_volume = (
    fda.read_oct_volume()
)  # returns an OCT volume with additional metadata if available
oct_volume.peek()  # plots a montage of the volume
oct_volume.save("fda_testing.avi")  # save volume as a movie
oct_volume.save(
    "fda_testing.png"
)  # save volume as a set of sequential images, fds_testing_[1...N].png

fundus_image = (
    fda.read_fundus_image()
)  # returns a  Fundus image with additional metadata if available
# fundus_image.save('mark_test.jpg')
fundus_image.save("fda_testing_fundus.jpg")
