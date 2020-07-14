"""
  Copyright 2018-2020 National Geographic Society

  Use of this software does not constitute endorsement by National Geographic
  Society (NGS). The NGS name and NGS logo may not be used for any purpose without
  written permission from NGS.

  Licensed under the Apache License, Version 2.0 (the "License"); you may not use
  this file except in compliance with the License. You may obtain a copy of the
  License at

      https://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software distributed
  under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
  CONDITIONS OF ANY KIND, either express or implied. See the License for the
  specific language governing permissions and limitations under the License.
"""

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
