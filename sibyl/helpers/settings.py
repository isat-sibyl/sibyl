import logging
import yaml
import os
from .version import version

from typing import List


class Settings:
    """A class to hold the settings from settings.yaml."""

    root: str = "/"
    default_locale: str = "en"
    open_browser: bool = True
    debug: bool = False

    max_component_nesting: int = 100
    components_paths: List[str] = ["components", "{$SIBYL_PATH}/components"]
    layouts_paths: List[str] = ["layouts", "{$SIBYL_PATH}/layouts"]
    root_folders: List[str] = ["favicon"]

    pages_path: str = "pages"
    build_path: str = "dist"
    locales_path: str = "locales"
    static_path: str = "static"

    cdn_url: str = f"https://cdn.sibyl.dev/{version}"

    treat_warnings_as_errors: bool = False

    dev_port: int = 8080
    websockets_port: int = 8081

    def __init__(self, path: str = "settings.yaml"):
        """Load the settings from settings.yaml."""
        # set env var SIBYL_PATH as os.path.dirname(__file__)
        with open(path, "r", encoding="utf-8") as file:
            result = yaml.load(file, Loader=yaml.BaseLoader)
            os.environ["SIBYL_PATH"] = os.path.dirname(os.path.dirname(__file__))
            result = Settings.replace_env_vars(result)

        # validate the settings. They must have the correct key and either not exist or be of the correct type
        for key, value in result.items():
            if value is None:
                continue
            if not hasattr(self, key):
                raise ValueError(f"Invalid setting '{key}'")
            if type(getattr(self, key)) == bool:
                value = bool(value)
            elif type(getattr(self, key)) == int:
                value = int(value)
            if not isinstance(value, type(getattr(self, key))):
                raise ValueError(
                    f"Invalid type for setting '{key}'. Expected {type(getattr(self, key))} but got {type(value)}"
                )
            setattr(self, key, value)
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)

    @staticmethod
    def replace_env_vars(var):
        """Replace all instances of $ENV_VAR with the value of the environment variable."""
        if isinstance(var, str):
            return os.path.expandvars(var)
        elif isinstance(var, dict):
            for key, value in var.items():
                var[key] = Settings.replace_env_vars(value)
            return var
        elif isinstance(var, list):
            for i in range(len(var)):
                var[i] = Settings.replace_env_vars(var[i])
            return var
