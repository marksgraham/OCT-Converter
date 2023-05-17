from __future__ import annotations

from datetime import datetime
from pathlib import Path

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
    """Class to hold an OCT volume and any related metadata.

    Also provides methods for viewing and saving.

    Attributes:
        volume: all the volume's b-scans.

        patient_id: patient ID.
        first_name: patient first name.
        surname: patient second name.
        sex: patient sex.
        DOB: patient date of birth.

        volume_id: volume ID.
        acquisition_date: date image acquired.
        num_slices: number of b-scans present in volume.
        laterality: left or right eye.

        contours: contours data.
        pixel_spacing: (x, y, z) pixel spacing in mm.
        metadata: all metadata available in the OCT scan.
    """

    def __init__(
        self,
        volume: list[np.array],
        patient_id: str | None = None,
        first_name: str | None = None,
        surname: str | None = None,
        sex: str | None = None,
        patient_dob: str | None = None,
        volume_id: str | None = None,
        acquisition_date: datetime | None = None,
        laterality: str | None = None,
        contours: dict | None = None,
        pixel_spacing: list[float] | None = None,
        metadata: dict | None = None,
    ) -> None:
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

        # geom data
        self.pixel_spacing = pixel_spacing

        # metadata
        self.metadata = metadata

    def peek(
        self,
        rows: int = 5,
        cols: int = 5,
        filepath: str | Path | None = None,
        show_contours: bool | None = False,
    ) -> None:
        """Plots a montage of the OCT volume. Optionally saves the plot if a filepath is provided.

        Args:
            rows: number of rows in the plot.
            cols: number of columns in the plot.
            filepath: location to save montage to.
            show_contours: if set to ``True``, will plot contours on the OCT volume.
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

    def save(self, filepath: str | Path) -> None:
        """Saves OCT volume as a video or stack of slices.

        Args:
            filepath: location to save volume to. Extension must be in VIDEO_TYPES or IMAGE_TYPES.
        """
        extension = Path(filepath).suffix
        if extension.lower() in VIDEO_TYPES:
            video_writer = imageio.get_writer(filepath, macro_block_size=None)
            for slice in self.volume:
                slice = slice.astype("uint8")
                video_writer.append_data(slice)
            video_writer.close()
        elif extension.lower() in IMAGE_TYPES:
            base = Path(filepath).stem
            print(
                "Saving OCT as sequential slices {}_[1..{}]{}".format(
                    base, len(self.volume), extension
                )
            )
            full_base = Path(filepath).with_suffix("")
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

    def get_projection(self) -> np.array:
        """Produces a 2D projection image from the volume."""
        projection = np.mean(self.volume, axis=1)
        return projection

    def save_projection(self, filepath: str | Path) -> None:
        """Save a 2D projection image from the volume.

        Args:
            filepath: location to save volume to. Extension must be in IMAGE_TYPES.
        """
        extension = Path(filepath).suffix
        if extension.lower() in IMAGE_TYPES:
            projection = self.get_projection()
            projection = 255 * projection / projection.max()
            cv2.imwrite(filepath, projection.astype(int))
        else:
            raise NotImplementedError(
                "Saving with file extension {} not supported".format(extension)
            )
