from filetypes import FDS
import matplotlib.pyplot as plt

filepath = '../file.fds'
fds = FDS(filepath)

oct_volume = fds.read_oct_volume()
plt.imshow(oct_volume[:,:,0]) # plot first slice

fundus_image = fds.read_fundus_image()
plt.imshow(fundus_image)


