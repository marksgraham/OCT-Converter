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
    deneme = filepath.split("/")[-1].split(".")[0]
    patient_folder = f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}"
    if not os.path.exists(patient_folder):
        os.mkdir(patient_folder)
    oct_volume = (
        fda.read_oct_volume()
    )  # returns an OCT volume with additional metadata if available
    oct_volume.peek()  # plots a montage of the volume
    oct_volume.save(
        f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}/{filepath.split('/')[-1].split('.')[0]}.avi"
    )  # save volume as a movie
    oct_volume.save(
        f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}/{filepath.split('/')[-1].split('.')[0]}.png"
    )  # save volume as a set of sequential images, fda_filename_[1...N].png

    fundus_image = (
        fda.read_fundus_image()
    )  # returns a  Fundus image with additional metadata if available
    fundus_image.save(
        f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}/{filepath.split('/')[-1].split('.')[0]}_fundus.jpg"
    )
    # save Fundus image to output directory, fda_filename_fundus.jpg

    fundus_grayscale_image = (
        fda.read_fundus_image_gray_scale()
    )  # returns a  Fundus image with additional metadata if available
    fundus_grayscale_image.save(
        f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}/{filepath.split('/')[-1].split('.')[0]}_grayscale_fundus.jpg"
    )
    # save Fundus image to output directory, fda_filename_grayscale_fundus.jpg

    # preparing json for other datas in fda file
    output_json = dict()
    output_json["fda_file_info"] = fda.read_fda_file_info()
    output_json["hardware_info"] = fda.read_hardware_info()
    output_json["patient_info"] = fda.read_patient_info()
    output_json["capture_info"] = fda.read_capture_info()
    output_json["param_scan"] = fda.read_param_scan()
    output_json["param_obs"] = fda.read_param_obs()
    output_json["img_mot_comp"] = fda.read_img_mot_comp()
    output_json["img_projection"] = fda.read_img_projection()
    output_json["regist_info"] = fda.read_regist_info()
    output_json["contour_info"] = fda.read_contour_info()
    output_json["effective_scan_range"] = fda.read_effective_scan_range()
    output_json["cornea_curve_result"] = fda.read_cornea_curve_result_info()
    output_json["cornea_thickness"] = fda.read_result_cornea_thickness()

    info_json = json.dumps(output_json)
    json_name = filepath.split("/")[-1].split(".")[0]
    with open(f"{patient_folder}/{json_name}.json", "w") as outfile:
        outfile.write(info_json)


extract_fda_with_images_and_json("your_fda_file_path", "your_output_path")
