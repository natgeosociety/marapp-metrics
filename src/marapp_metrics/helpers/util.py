import json
from contextlib import contextmanager
from os import path


class DataReadException(Exception):
    pass


@contextmanager
def file_reader(filename):
    relative_filename = path.join("..", path.dirname(__file__), filename)
    file = open(relative_filename)
    try:
        yield file
    finally:
        file.close()


def json_reader(filename):
    try:
        with file_reader(filename) as file:
            data = file.read()
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise DataReadException(f"Could not decode data at: {filename}")
    except Exception:
        raise FileNotFoundError(f"Could not find filename: {filename}")
