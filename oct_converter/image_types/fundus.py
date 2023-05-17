from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

VIDEO_TYPES = [
    ".avi",
    ".mp4",
]
IMAGE_TYPES = [".png", ".bmp", ".tiff", ".jpg", ".jpeg"]


class FundusImageWithMetaData(object):
    """Class to hold a fundus image and any related metadata.

    Also provides methods for viewing and saving.

    Attributes:
        image: fundus image.
        laterality: left or right eye.
        patient_id: patient ID.
        image_id: image ID.
        DOB: patient date of birth.
    """

    def __init__(
        self,
        image: np.array,
        laterality: str | None = None,
        patient_id: str | None = None,
        image_id: str | None = None,
        patient_dob: str | None = None,
    ) -> None:
        self.image = image
        self.laterality = laterality
        self.patient_id = patient_id
        self.image_id = image_id
        self.DOB = patient_dob

    def save(self, filepath: str | Path) -> None:
        """Saves fundus image.

        Args:
            filepath: location to save volume to. Extension must be in IMAGE_TYPES.
        """
        extension = Path(filepath).suffix
        if extension.lower() in IMAGE_TYPES:
            # change channel order from RGB to BGR and save with cv2
            image = cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(filepath, image)
        elif extension.lower() == ".npy":
            np.save(filepath, self.image)
        else:
            raise NotImplementedError(
                "Saving with file extension {} not supported".format(extension)
            )
