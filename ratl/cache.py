import json
import logging


def load_json_cache(filename: str) -> dict:
    try:
        with open(filename, "r", encoding="UTF-8") as content:
            payload = json.loads(content.read())
            return payload if payload else {}
    except Exception as e:
        logging.warning(e)
        return {}


def save_json_cache(filename: str, payload: dict):
    with open(filename, "w+", encoding="UTF-8") as file:
        file.write(json.dumps(payload, indent=4))
