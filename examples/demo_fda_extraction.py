from oct_converter.readers import FDA

# a sample .fda file can be downloaded from the Biobank resource here:
# https://biobank.ndph.ox.ac.uk/showcase/refer.cgi?id=31

filepath = '/home/mark/Downloads/1000034_21011_0_0.fda'
fda = FDA(filepath)
fundus_image = fda.read_fundus_image()  # returns a  Fundus image with additional metadata if available
fundus_image.save('fda_testing_fundus.jpg')
