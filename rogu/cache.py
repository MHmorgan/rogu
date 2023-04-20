"""cache provides the cache functionality for Rogu.

cache has import side effects, and should only be imported locally.
"""
import atexit
import pickle
import shelve
from pathlib import Path

import config


def _open(path):
    return shelve.open(
        str(path),
        protocol=pickle.HIGHEST_PROTOCOL
    )


primary_file = Path(config.app_dir) / 'rogu-cache'
primary = _open(primary_file)
atexit.register(primary.close)

resources_file = Path(config.app_dir) / 'rogu-resource-cache'
resources = _open(resources_file)
atexit.register(resources.close)


def path(name):
    """Return the path to a cache file with the given name.
    Any missing parent directories will be created.

    :param name: string or Path.
    """
    p = Path(config.app_dir) / 'file-cache' / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
