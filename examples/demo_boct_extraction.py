from oct_converter.readers import BOCT

filepath = "../sample_files/sample.OCT"
boct = BOCT(filepath)
oct_volumes = boct.read_oct_volume(
    diskbuffered=True
)  # returns an OCT volume with additional metadata if available
for oct in oct_volumes:
    oct.peek()  # plots a montage of the volume
    oct.save("boct_testing.avi")  # save volume as a movie
    oct.save(
        "boct_testing.png"
    )  # save volume as a set of sequential images, fds_testing_[1...N].png
