import os

import cv2
import imageio
import matplotlib.pyplot as plt
import numpy as np

VIDEO_TYPES = [
    ".avi",
    ".mp4",
]
IMAGE_TYPES = [".png", ".bmp", ".tiff", ".jpg", ".jpeg"]


class OCTVolumeWithMetaData(object):
    """Class to hold the OCT volume and any related metadata, and enable viewing and saving.

    Attributes:
        volume (list of np.array): All the volume's b-scans.

        patient_id (str): Patient ID.
        first_name (str): Patient first name.
        surname (str): Patient second name.
        sex (str): Patient sex.
        DOB (str): Patient date of birth.

        volume_id (str): Volume ID.
        acquisition_date (datetime): date image acquired.
        num_slices (int): Number of b-scans present in volume.
        laterality (str): Left or right eye.
        contours (dict of list): Contours data.
    """

    def __init__(
        self,
        volume,
        patient_id=None,
        first_name=None,
        surname=None,
        sex=None,
        patient_dob=None,
        volume_id=None,
        acquisition_date=None,
        laterality=None,
        contours=None,
    ):
        # image
        self.volume = volume

        # patient data
        self.patient_id = patient_id
        self.first_name = first_name
        self.surname = surname
        self.sex = sex
        self.DOB = patient_dob

        # volume data
        self.volume_id = volume_id
        self.acquistion_date = acquisition_date
        self.laterality = laterality
        self.num_slices = len(self.volume)
        self.contours = contours

    def peek(self, rows=5, cols=5, filepath=None, show_contours=False):
        """Plots a montage of the OCT volume. Optionally saves the plot if a filepath is provided.

        Args:
            rows (int) : Number of rows in the plot.
            cols (int) : Number of columns in the plot.
            filepath (str): Location to save montage to.
            show_contours (bool): If set to ``True``, will plot contours on the OCT volume.
        """
        images = rows * cols
        x_size = rows * self.volume[0].shape[0]
        y_size = cols * self.volume[0].shape[1]
        ratio = y_size / x_size
        slices_indices = np.linspace(0, self.num_slices - 1, images).astype(np.int16)
        plt.figure(figsize=(12 * ratio, 12))
        for i in range(images):
            slice_id = slices_indices[i]
            plt.subplot(rows, cols, i + 1)
            plt.imshow(self.volume[slice_id], cmap="gray")
            if show_contours and self.contours is not None:
                for v in self.contours.values():
                    if (
                        slice_id < len(v)
                        and v[slice_id] is not None
                        and not np.isnan(v[slice_id]).all()
                    ):
                        plt.plot(v[slice_id], color="r")
            plt.axis("off")
            plt.title("{}".format(slice_id))
        plt.suptitle("OCT volume with {} slices.".format(self.num_slices))

        if filepath is not None:
            plt.savefig(filepath)
        else:
            plt.show()

    def save(self, filepath):
        """Saves OCT volume as a video or stack of slices.

        Args:
            filepath (str): Location to save volume to. Extension must be in VIDEO_TYPES or IMAGE_TYPES.
        """
        extension = os.path.splitext(filepath)[1]
        if extension.lower() in VIDEO_TYPES:
            video_writer = imageio.get_writer(filepath, macro_block_size=None)
            for slice in self.volume:
                video_writer.append_data(slice)
            video_writer.close()
        elif extension.lower() in IMAGE_TYPES:
            base = os.path.splitext(os.path.basename(filepath))[0]
            print(
                "Saving OCT as sequential slices {}_[1..{}]{}".format(
                    base, len(self.volume), extension
                )
            )
            full_base = os.path.splitext(filepath)[0]
            self.volume = np.array(self.volume).astype("float64")
            self.volume *= 255.0 / self.volume.max()
            for index, slice in enumerate(self.volume):
                filename = "{}_{}{}".format(full_base, index, extension)
                cv2.imwrite(filename, slice)
        elif extension.lower() == ".npy":
            np.save(filepath, self.volume)
        else:
            raise NotImplementedError(
                "Saving with file extension {} not supported".format(extension)
            )

    def get_projection(self):
        """Produces a 2D projection image from the volume."""
        projection = np.mean(self.volume, axis=1)
        return projection

    def save_projection(self, filepath):
        """Save a 2D projection image from the volume.

        Args:
            filepath (str): Location to save volume to. Extension must be in IMAGE_TYPES.
        """
        extension = os.path.splitext(filepath)[1]
        if extension.lower() in IMAGE_TYPES:
            projection = self.get_projection()
            projection = 255 * projection / projection.max()
            cv2.imwrite(filepath, projection.astype(int))
        else:
            raise NotImplementedError(
                "Saving with file extension {} not supported".format(extension)
            )
