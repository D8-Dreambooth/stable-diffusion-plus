import json
import logging
import os
from typing import Dict, List

from PIL import Image
from wordcloud import WordCloud

logger = logging.getLogger(__name__)


def get_frequencies(file_tags: Dict[str, List[str]]) -> Dict[str, int]:
    full_terms = {}
    for tag, files in file_tags.items():
        full_terms[tag] = len(files)
    return full_terms


def make_image(text: Dict[str, int]) -> Image.Image:
    wc = WordCloud(background_color="black", max_words=1000, width=1920, height=1080)
    # generate word cloud
    wc.generate_from_frequencies(text)
    return wc.to_image()


def process_file(file_path: str, tags_dict: Dict[str, List[str]]) -> None:
    try:
        with open(file_path, 'r') as file:
            for line in file:
                tags = [tag.strip() for tag in line.split(',')]
                for tag in tags:
                    tag = tag.lower()
                    if tag in tags_dict:
                        tags_dict[tag].append(file_path)
                    else:
                        tags_dict[tag] = [file_path]
    except UnicodeDecodeError:
        logger.warning(f"Failed to process file {file_path}")


def process_directory(directory_path: str, tags_dict: Dict[str, int], recurse: bool) -> None:
    for root, dirs, files in os.walk(directory_path):
        for file_name in files:
            if file_name.endswith('.txt'):
                file_path = os.path.join(root, file_name)
                process_file(file_path, tags_dict)
        # If not recursing, empty the dirs list in-place to prevent os.walk from processing subdirectories.
        if not recurse:
            dirs.clear()


def generate_word_cloud_from_dict(tags_dict: Dict[str, int]) -> Image.Image:
    # Convert the dictionary to a string of words
    frequency_dict = get_frequencies(tags_dict)
    return make_image(frequency_dict)


def save_to_json(tags_dict: Dict[str, int], json_file: str) -> None:
    with open(json_file, 'w') as file:
        json.dump(tags_dict, file)


def make_cloud(directory_path: str, recurse: bool) -> Image.Image:
    tags_dict = {}
    logger.debug(f"Processing directory {directory_path}")
    process_directory(directory_path, tags_dict, recurse)
    logger.debug(f"Processed directory {directory_path}")
    return generate_word_cloud_from_dict(tags_dict), tags_dict
