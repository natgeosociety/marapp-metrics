import functools
import os

import yaml


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
        with open(filename, "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError:
                raise ConfigurationException(
                    f"Could not find config file at: {config_filepath}"
                )


def deepgetattr(obj, attr, default=None, sep="."):
    """Recurse through an attribute chain to get the ultimate value."""

    return functools.reduce(lambda o, key: o.get(key, default), attr.split(sep), obj)
