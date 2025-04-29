from utils.paths import SETTINGS_PATH
import yaml

def load_config(path=SETTINGS_PATH) -> dict:
    with open(path, "r") as file:
        return yaml.safe_load(file)
