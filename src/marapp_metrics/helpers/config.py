import functools
import os

import yaml

from .logging import get_logger

logger = get_logger("config")


class ConfigurationException(Exception):
    pass


class Config:
    def __init__(self, config_filepath):
        self._config = self._load_config_object(config_filepath)

    def get_property(self, property_path, default=None):
        prop = deepgetattr(self._config, property_path, default)
        if prop is None:
            raise ConfigurationException(f"Could not get property at: {property_path}")
        return prop

    @staticmethod
    def _load_config_object(config_filepath):
        root = os.path.dirname(os.path.dirname(__file__))
        filename = os.path.join(root, config_filepath)
        try:
            with open(filename, "r") as stream:
                try:
                    config = yaml.safe_load(stream)
                    logger.debug(f"Using earthengine config from: {config_filepath}")
                    return config
                except yaml.YAMLError:
                    raise
        except Exception:
            raise ConfigurationException(
                f"Could not find earthengine config: {config_filepath}"
            )


def deepgetattr(obj, attr, default=None, sep="."):
    """Recurse through an attribute chain to get the ultimate value."""

    return functools.reduce(lambda o, key: o.get(key, default), attr.split(sep), obj)
