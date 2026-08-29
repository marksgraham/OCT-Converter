from __future__ import annotations

import struct
import warnings
from datetime import datetime

import cv2
import numpy as np

from oct_converter.image_types.ivcm import IVCMImageWithMetaData
from oct_converter.readers.binary_structs import e2e_binary
from oct_converter.readers.e2e import E2E


class IVCM(E2E):
    """Class for extracting IVCM data from Heidelberg's .e2e file format.

    Notes:
        Mostly based on description of .e2e file format here:
        https://bitbucket.org/uocte/uocte/wiki/Heidelberg%20File%20Format.

    Attributes:
        filepath: path to .e2e file for reading.
    """

    def read_ivcm_image(self) -> list[IVCMImageWithMetaData]:
        """Reads IVCM data from Heidelberg HRT-RCM .e2e files.

        Returns raw JPEG frames without post-processing. Note that the Heidelberg
        software applies additional cropping and spatial corrections on export, so
        exported TIFFs will differ from these raw frames.

        Returns:
            A list of IVCMImageWithMetaData.
        """
        IVCM_FLAGS = 0x02010101

        with open(self.filepath, "rb") as f:
            chunk_stack = []
            for position in self.directory_stack:
                f.seek(position + self.byte_skip)
                raw = f.read(52)
                directory_chunk = e2e_binary.main_directory_structure.parse(raw)
                for ii in range(directory_chunk.num_entries):
                    raw = f.read(44)
                    chunk = e2e_binary.sub_directory_structure.parse(raw)
                    if chunk.start > chunk.pos:
                        chunk_stack.append([chunk.start, chunk.size])

            volume_dict: dict[str, dict[int, np.ndarray]] = {}
            z_pos_dict: dict[str, dict[int, int]] = {}
            laterality_dict: dict[str, str] = {}
            laterality = None

            for start, size in chunk_stack:
                f.seek(start + self.byte_skip)
                raw = f.read(60)
                try:
                    chunk = e2e_binary.chunk_structure.parse(raw)
                except Exception:
                    continue

                if chunk.type == 9:  # patient data
                    raw = f.read(127)
                    try:
                        patient_data = e2e_binary.patient_id_structure.parse(raw)
                        self.sex = patient_data.sex
                        self.first_name = patient_data.first_name
                        self.surname = patient_data.surname
                        self.patient_id = patient_data.patient_id
                        if len(str(patient_data.birthdate)) == 8:
                            self.birthdate = str(patient_data.birthdate)
                        else:
                            try:
                                julian_birthdate = (patient_data.birthdate / 64) - 14558805
                                self.birthdate = self.julian_to_ymd(julian_birthdate)
                            except ValueError:
                                self.birthdate = None
                    except Exception:
                        pass

                elif chunk.type == 3:  # scan preamble / laterality
                    raw = f.read(chunk.size)
                    try:
                        pre_data = e2e_binary.pre_data.parse(raw)
                        if pre_data.laterality in ["R", "L"]:
                            laterality = pre_data.laterality
                    except Exception:
                        laterality = None
                    volume_string = "{}_{}_{}".format(
                        chunk.patient_db_id, chunk.study_id, chunk.series_id
                    )
                    if laterality and (volume_string not in laterality_dict):
                        laterality_dict[volume_string] = laterality

                elif chunk.type == 10031:  # IVCM acquisition timestamp (Unix, big-endian)
                    raw = f.read(chunk.size)
                    if len(raw) >= 4 and self.acquisition_date is None:
                        try:
                            unix_ts = struct.unpack_from(">I", raw)[0]
                            self.acquisition_date = datetime.fromtimestamp(unix_ts)
                        except Exception:
                            pass

                elif chunk.type == 10002:  # per-frame IVCM metadata
                    raw = f.read(chunk.size)
                    try:
                        frame_meta = e2e_binary.ivcm_frame_metadata.parse(raw)
                        volume_string = "{}_{}_{}".format(
                            chunk.patient_db_id, chunk.study_id, chunk.series_id
                        )
                        if volume_string not in z_pos_dict:
                            z_pos_dict[volume_string] = {}
                        z_pos_dict[volume_string][chunk.slice_id] = frame_meta.z_pos_um
                    except Exception:
                        pass

                elif chunk.type == 1073741824 and chunk.ind == 0:
                    raw = f.read(16)
                    if len(raw) < 16:
                        continue
                    try:
                        mini = e2e_binary.ivcm_image_structure.parse(raw)
                    except Exception:
                        continue

                    if mini.flags != IVCM_FLAGS:
                        continue

                    jpeg_data = f.read(mini.jpeg_size)
                    if len(jpeg_data) < 2 or jpeg_data[:2] != b"\xff\xd8":
                        continue

                    try:
                        image = cv2.imdecode(
                            np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_UNCHANGED
                        )
                        if image is None:
                            raise ValueError("cv2.imdecode returned None")
                    except Exception as e:
                        warnings.warn(
                            f"Could not decode IVCM JPEG for chunk at {start}: {e}",
                            UserWarning,
                        )
                        continue

                    volume_string = "{}_{}_{}".format(
                        chunk.patient_db_id, chunk.study_id, chunk.series_id
                    )
                    if volume_string not in volume_dict:
                        volume_dict[volume_string] = {}
                    volume_dict[volume_string][chunk.slice_id] = image

            ivcm_images = []
            for key, slices in volume_dict.items():
                sorted_ids = sorted(slices.keys())
                sorted_frames = [slices[k] for k in sorted_ids]
                frames = np.stack(sorted_frames, axis=0)

                z_positions = None
                if key in z_pos_dict:
                    z_positions = [z_pos_dict[key].get(k) for k in sorted_ids]

                ivcm_images.append(
                    IVCMImageWithMetaData(
                        frames=frames,
                        z_pos_um=z_positions,
                        patient_id=self.patient_id,
                        first_name=self.first_name,
                        surname=self.surname,
                        sex=self.sex,
                        patient_dob=self.birthdate,
                        acquisition_date=self.acquisition_date,
                        series_id=key,
                        laterality=laterality_dict.get(key),
                    )
                )

        return ivcm_images
