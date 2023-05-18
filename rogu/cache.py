"""Provides caches and cache functionality.

This has import side effects, and should only be imported locally.
"""
import atexit
import pickle
import shelve
from pathlib import Path
from typing import Union

import config


def _open(file: Union[str, Path]) -> shelve.Shelf:
    return shelve.open(str(file), protocol=pickle.HIGHEST_PROTOCOL)


primary_file = Path(config.app_dir) / 'rogu-cache'
primary = _open(primary_file)
atexit.register(primary.close)

resources_file = Path(config.app_dir) / 'rogu-resource-cache'
resources = _open(resources_file)
atexit.register(resources.close)

_caches = {}


def __getattr__(name: Union[str, Path]) -> shelve.Shelf:
    """Return a cache with the given name.

    :param name: string or Path.
    """
    if name not in _caches:
        _caches[name] = _open(path(name))
        atexit.register(_caches[name].close)
    return _caches[name]


def get(name: Union[str, Path]) -> shelve.Shelf:
    """Return a cache with the given name.

    :param name: string or Path.
    """
    return __getattr__(name)


def path(name: Union[str, Path]) -> Path:
    """Return the path to a cache file with the given name.
    Any missing parent directories will be created.

    :param name: string or Path.
    """
    p = Path(config.app_dir) / 'file-cache' / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
