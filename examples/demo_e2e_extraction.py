from oct_converter.readers import E2E

filepath = "/Users/mark/Library/CloudStorage/Dropbox/Work/Projects/OCT-Converter/my_example_volumes/e2e-vassily/PatientIDTIN0007-ADAMIDIS/DIMIT001.E2E"
filepath = "/Users/mark/Library/CloudStorage/Dropbox/Work/Projects/OCT-Converter/my_example_volumes/e2e-vassily/PatientIDTIN0007-ADAMIDIS/DIMIT002.E2E"
# filepath = "/Users/mark/Library/CloudStorage/Dropbox/Work/Projects/OCT-Converter/my_example_volumes/e2e-vassily/new-e2e-11-06-2022/TIN0901T.E2E"
# filepath = "/Users/mark/Library/CloudStorage/Dropbox/Work/Projects/OCT-Converter/my_example_volumes/e2e-vassily/new-e2e-11-06-2022/TIN0902T.E2E"
# filepath = "/Users/mark/Library/CloudStorage/Dropbox/Work/Projects/OCT-Converter/my_example_volumes/e2e-vassily/problem20-06-22/ADAMI02I.E2E"
filepath = "/Users/mark/Library/CloudStorage/Dropbox/Work/Projects/OCT-Converter/my_example_volumes/e2e-vassily/TIN0001T.E2E"
file = E2E(filepath)
oct_volumes = (
    file.read_oct_volume()
)  # returns a list of all OCT volumes with additional metadata if available
for volume in oct_volumes:
    volume.peek(show_contours=True)  # plots a montage of the volume
    volume.save("{}_{}.avi".format(volume.volume_id, volume.laterality))

fundus_images = (
    file.read_fundus_image()
)  # returns a list of all fundus images with additional metadata if available
for image in fundus_images:
    image.save("{}+{}.png".format(image.image_id, image.laterality))
