from oct_converter.readers import E2E


filepath = '/Users/mark/Downloads/Sample/001_O01S.E2E'
file = E2E(filepath)
oct_volumes = file.read_oct_volume()  # returns a list of all OCT volumes with additional metadata if available
for volume in oct_volumes:
    volume.peek() # plots a montage of the volume
    volume.save('{}.avi'.format(volume.patient_id))

fundus_images = file.read_fundus_image() #returns a list of all fundus images with additional metadata if available
for image in fundus_images:
    image.save('{}.png'.format(image.patient_id))
