from utils.paths import SETTINGS_PATH
import yaml
from utils.paths import PILLAR_CONFIG_PATH
import json

def load_config(path=SETTINGS_PATH) -> dict:
    with open(path, "r") as file:
        return yaml.safe_load(file)

def load_pillar_config(path=PILLAR_CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
