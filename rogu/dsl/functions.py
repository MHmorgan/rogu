"""
function implements the functions available in the DSL.
"""

import os
from contextlib import AbstractContextManager

from .types import DslType


class chdir(AbstractContextManager):
    """Change work directory.

    May be used as a context manager or function.
    """

    def __init__(self, path):
        self._old_cwd = [os.getcwd()]
        os.chdir(path)

    def __exit__(self, *excinfo):
        os.chdir(self._old_cwd.pop())


def exists(o):
    """Check if object exists."""
    if isinstance(o, DslType):
        o = o.path
    return os.path.exists(o)


def fetch(uri):
    """Fetch a resource from the given URI."""

