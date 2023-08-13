import os
import shutil
import fnmatch
from PIL import Image
import hashlib
import numpy as np

SEARCH_DIR = "E:\\dev\\stable-diffusion-plus\\data_protected\\users\\admin\\clean"  # Replace with your path

# Start with a huge number
min_dim = 1e6
hash_dict = {}


def get_image_hash(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def enumerate_files(directory, file_dict):
    global min_dim
    dirs_to_search = os.listdir(directory)
    if len(dirs_to_search) == 0:
        dirs_to_search = [directory]
    for subdir in dirs_to_search:
        subdir_path = os.path.join(directory, subdir)
        if os.path.isdir(subdir_path):
            for root, dirnames, filenames in os.walk(subdir_path):
                images = fnmatch.filter(filenames, '*.jpg') + fnmatch.filter(filenames, '*.png')
                if images:
                    key = subdir
                    if key not in file_dict:
                        file_dict[key] = []
                    for img in images:
                        img_path = os.path.join(root, img)
                        image = Image.open(img_path)
                        min_dim = min(min_dim, min(image.size))
                        file_dict[key].append(img_path)
    return file_dict


def create_output_dirs(file_dict, search_directory):
    global min_dim, hash_dict
    out_dir = os.path.dirname(search_directory)
    for key, files in file_dict.items():
        output_dir = os.path.join(out_dir, 'output', key)
        os.makedirs(output_dir, exist_ok=True)
        for index, file in enumerate(files):
            image = Image.open(file)
            aspect_ratio = max(image.size) / min(image.size)
            new_size = (int(min_dim * aspect_ratio), min_dim) if image.width < image.height else (
                min_dim, int(min_dim * aspect_ratio))
            resized_image = image.resize(new_size, Image.LANCZOS)

            file_name, file_ext = os.path.splitext(file)
            target_file = os.path.join(output_dir, str(index).zfill(6) + file_ext)
            image_hash = get_image_hash(resized_image)
            if image_hash in hash_dict.keys():
                # Figure out which image is larger
                if np.prod(image.size) < np.prod(Image.open(hash_dict[image_hash]).size):
                    print(f"Warning: Image {file} appears to be a duplicate of {hash_dict[image_hash]}, skipping.")
                    continue
                else:
                    # Update hash with new image
                    print(f"Replacing smaller image with larger image from {file}")
                    target_file = hash_dict[image_hash]
            hash_dict[image_hash] = target_file
            shutil.copy2(file, target_file)
            # Replace image extension with .txt
            txt_file = file.replace(file_ext, '.txt')
            target_txt = target_file.replace(file_ext, '.txt')
            if os.path.isfile(txt_file):
                shutil.copy2(txt_file, target_txt)


def main():
    file_dict = {}
    file_dict = enumerate_files(SEARCH_DIR, file_dict)

    create_output_dirs(file_dict, SEARCH_DIR)


if __name__ == "__main__":
    main()
