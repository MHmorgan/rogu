"""cache provides the cache functionality for Rogu.

cache has import side effects, and should only be imported locally.
"""
import atexit
import pickle
import shelve
from pathlib import Path

import config

__all__ = ['primary', 'resources']


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
