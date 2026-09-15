from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2
import imageio
import numpy as np

VIDEO_TYPES = [
    ".avi",
    ".mp4",
]
IMAGE_TYPES = [".png", ".bmp", ".tiff", ".jpg", ".jpeg"]


class IVCMImageWithMetaData(object):
    """Class to hold an IVCM (in vivo confocal microscopy) image stack and metadata.

    Also provides methods for saving.

    Attributes:
        frames: en-face confocal images ordered by focal depth.
        z_pos_um: focal depth in micrometres for each frame.

        patient_id: patient ID.
        first_name: patient first name.
        surname: patient second name.
        sex: patient sex.
        DOB: patient date of birth.

        acquisition_date: date image acquired.
        laterality: left or right eye.
        series_id: series identifier from the source file.
    """

    def __init__(
        self,
        frames: np.ndarray,
        z_pos_um: list[int | None] | None = None,
        patient_id: str | None = None,
        first_name: str | None = None,
        surname: str | None = None,
        sex: str | None = None,
        patient_dob: str | None = None,
        acquisition_date: datetime | None = None,
        laterality: str | None = None,
        series_id: str | None = None,
    ) -> None:
        # image
        self.frames = frames
        self.z_pos_um = z_pos_um

        # patient data
        self.patient_id = patient_id
        self.first_name = first_name
        self.surname = surname
        self.sex = sex
        self.DOB = patient_dob

        # acquisition data
        self.acquisition_date = acquisition_date
        self.laterality = laterality
        self.series_id = series_id

    def save(self, filepath: str | Path) -> None:
        """Saves IVCM frames as a video or stack of images.

        Args:
            filepath: location to save frames to. Extension must be in VIDEO_TYPES or IMAGE_TYPES.
        """
        extension = Path(filepath).suffix
        if extension.lower() in VIDEO_TYPES:
            writer = imageio.get_writer(filepath, macro_block_size=None)
            for frame in self.frames:
                writer.append_data(frame.astype("uint8"))
            writer.close()
        elif extension.lower() in IMAGE_TYPES:
            base = Path(filepath).with_suffix("")
            for index, frame in enumerate(self.frames):
                cv2.imwrite(str(base) + f"_{index}{extension}", frame)
        elif extension.lower() == ".npy":
            np.save(filepath, self.frames)
        else:
            raise NotImplementedError(
                "Saving with file extension {} not supported".format(extension)
            )
