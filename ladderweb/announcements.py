import os.path
from typing import Tuple

import yaml


def get_announcements(announcements_yaml_file: str) -> list[Tuple[str, str]]:
    """Reads date/message tuples from a yaml file

    Returns
    -------
    list[Tuple[str, str]]
    """
    if os.path.exists(announcements_yaml_file):
        with open(announcements_yaml_file, "r") as file:
            yaml_content = yaml.safe_load(file)
            return [(date, msg) for date, msg in yaml_content.items()]
    return []
