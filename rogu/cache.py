"""
cache provides the cache functionality for Rogu.
"""
import atexit
import pickle
import shelve
from pathlib import Path

import config

__all__ = ['cache']

_cache_file = Path(config.app_dir) / 'cache.yaml'

cache = shelve.open(str(_cache_file), protocol=pickle.HIGHEST_PROTOCOL)

atexit.register(cache.close)
