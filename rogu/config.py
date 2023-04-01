"""
config provides the global configuration for the rogu app.
"""

from os import environ
from pathlib import Path

import click
import yaml

__all__ = [
    'version',
    'config_keys',
    'environment_variables',
    'set_',
    'reset',
]

version = '0.1'

_defaults = {
    'ugor_url': 'https://ugor.hirth.dev',
    'app_dir': click.get_app_dir('rogu', force_posix=True),
    'bin_dir': str(Path.home() / 'bin'),

    'git_branch': 'main',
    'git_remote': None,
    'git_user': None,
    'git_name': None,
    'git_email': None,
}

_env_vars = {
    key: f'ROGU_{key.upper()}'
    for key in _defaults
}

config_keys = list(_defaults.keys())
environment_variables = list(_env_vars.values())

_config_file = Path(environ.get('ROGU_APP_DIR', _defaults['app_dir'])) / 'config.yaml'


def _read_config():
    if not _config_file.exists():
        return {}
    with _config_file.open() as f:
        return yaml.full_load(f)


_conf = _read_config()


def __getattr__(name):
    if name not in _defaults:
        raise AttributeError(name)
    if _env_vars[name] in environ:
        return environ[_env_vars[name]]
    if name in _conf:
        return _conf[name]
    return _defaults[name]


def set_(key, value):
    _conf[key] = value
    with _config_file.open('w') as f:
        yaml.dump(_conf, f)


def reset(key):
    if key in _conf:
        del _conf[key]
    with _config_file.open('w') as f:
        yaml.dump(_conf, f)
