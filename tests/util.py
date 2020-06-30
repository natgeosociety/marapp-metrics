import os
import logging

import functools
import geopandas as gpd
import json
from contextlib import contextmanager
from os import path

logger = logging.getLogger()


class DataReadException(Exception):
    pass


class GeoJSONReadException(Exception):
    pass


@contextmanager
def file_reader(filename):
    relative_filename = path.join("..", path.dirname(__file__), filename)
    file = open(relative_filename, "r")
    try:
        yield file
    finally:
        file.close()


def json_reader(filename, ignore_missing=False):
    try:
        with file_reader(filename) as file:
            data = file.read()
            return json.loads(data)
    except FileNotFoundError as e:
        if not ignore_missing:
            raise e
    except json.JSONDecodeError:
        raise DataReadException(f"Could not decode data at: {filename}")
    return None


def json_writer(filename, data):
    relative_filename = path.join("..", path.dirname(__file__), filename)
    if not os.path.isfile(relative_filename):
        directory = os.path.dirname(relative_filename)
        os.makedirs(directory, exist_ok=True)

        logger.warning(f"creating fixture for: {relative_filename}")
    with open(relative_filename, "w") as file:
        file.write(json.dumps(data, indent=2))


def geojson_reader(filename):
    with file_reader(filename) as file:
        try:
            return gpd.read_file(file.name)
        except Exception:
            raise GeoJSONReadException(f"Could not decode GeoJSON at: {filename}")


def traverse_nested(value, key_path=None, sep="."):
    """Deeply traverse a nested dictionary while keeping the full path of the keys."""

    if not key_path:
        key_path = []
    if isinstance(value, dict):
        for k, v in value.items():
            local_path = key_path[:]
            local_path.append(k)
            yield from traverse_nested(v, local_path)
    else:
        yield sep.join(key_path), value


def deepgetattr(obj, attr, default=None, sep="."):
    """Recurse through an attribute chain to get the ultimate value."""

    return functools.reduce(lambda o, key: o.get(key, default), attr.split(sep), obj)
