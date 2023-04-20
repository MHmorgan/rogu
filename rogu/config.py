"""config provides the global configuration for the rogu app.

config has import side effects, and should only be imported locally.
"""

import atexit
import shutil
import tempfile
from os import environ
from pathlib import Path

import click
import yaml

__all__ = [
    'version',
    'set_',
    'reset',

    'ugor_url',
    'app_dir',
]

version = '0.1'

defaults = {
    'ugor_url': 'https://ugor.hirth.dev',
    'app_dir': click.get_app_dir('rogu', force_posix=True),
}

env_vars = {
    key: f'ROGU_{key.upper()}'
    for key in defaults
}

# Temporary directory, unique for each run
tmp_dir = Path(tempfile.mkdtemp(prefix='rogu-'))

atexit.register(lambda: tmp_dir.exists() and shutil.rmtree(tmp_dir, ignore_errors=True))


# ------------------------------------------------------------------------------
# Config interface

def _read_config():
    if not _file.exists():
        return {}
    with _file.open() as f:
        return yaml.full_load(f)


_file = Path(environ.get('ROGU_APP_DIR', defaults['app_dir'])) / 'config.yaml'
_config = _read_config()


def __getattr__(name):
    if name not in defaults:
        raise AttributeError(name)
    if env_vars[name] in environ:
        return environ[env_vars[name]]
    if name in _config:
        return _config[name]
    return defaults[name]


def set_(key, value):
    _config[key] = value
    with _file.open('w') as f:
        yaml.dump(_config, f)


def reset(key):
    if key in _config:
        del _config[key]
    with _file.open('w') as f:
        yaml.dump(_config, f)
