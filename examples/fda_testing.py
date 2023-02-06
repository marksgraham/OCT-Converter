import json
import os

from oct_converter.readers import FDA


def extract_fda_with_images_and_json(fda_file_path, output_dir):
    """
    Function takes the fda file and extract it on a directory with images and info json.
    :param fda_file_path: local path of fda file.
    :param output_dir: output directory path where the images and json will be extract.
    :return: nothing.
    """
    filepath = fda_file_path
    fda = FDA(filepath)
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    patient_folder = f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}"
    if not os.path.exists(patient_folder):
        os.mkdir(patient_folder)
    oct_volume = (
        fda.read_oct_volume()
    )  # returns an OCT volume with additional metadata if available
    if oct_volume is not None:
        oct_volume.peek()  # plots a montage of the volume
        oct_volume.save(
            f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}/{filepath.split('/')[-1].split('.')[0]}.avi"
        )  # save volume as a movie
        oct_volume.save(
            f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}/{filepath.split('/')[-1].split('.')[0]}.png"
        )  # save volume as a set of sequential images, fda_filename_[1...N].png
    else:
        print("There is no oct volume in fda file.")

    fundus_image = (
        fda.read_fundus_image()
    )  # returns a  Fundus image with additional metadata if available
    if fundus_image is not None:
        fundus_image.save(
            f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}/{filepath.split('/')[-1].split('.')[0]}_fundus.jpg"
        )
    else:
        print("There is no fundus image data in fda file.")
    # save Fundus image to output directory, fda_filename_fundus.jpg

    fundus_grayscale_image = (
        fda.read_fundus_image_gray_scale()
    )  # returns a  Fundus image with additional metadata if available
    if fundus_grayscale_image is not None:
        fundus_grayscale_image.save(
            f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}/{filepath.split('/')[-1].split('.')[0]}_grayscale_fundus.jpg"
        )
    else:
        print("There is no grayscale fundus image data in fda file.")
    # save Fundus image to output directory, fda_filename_grayscale_fundus.jpg

    # preparing json for other datas in fda file
    chunk_dict = fda.get_list_of_file_chunks(printing=False)
    output_json = dict()
    for key in chunk_dict.keys():
        if key in [
            b"@IMG_JPEG",
            b"@IMG_FUNDUS",
            b"@IMG_TRC_02",
        ]:  # this chunks are image chunks and extract with another methods
            continue
        json_key = key.decode().split("@")[-1].lower()
        try:
            output_json[json_key] = fda.read_any_info_and_make_dict(key)
        except KeyError:
            print(f"{key} there is no method for getting info from this chunk.")

    info_json = json.dumps(output_json)
    json_name = filepath.split("/")[-1].split(".")[0]
    with open(f"{patient_folder}/{json_name}.json", "w") as outfile:
        outfile.write(info_json)


extract_fda_with_images_and_json("your fda file path", "your output path")
