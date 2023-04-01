"""
types defines the types used in RDSL.
"""

import abc
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    'DslType',
    'Archive',
    'File',
    'Repo',
    'Resource',
]


class DslType(abc.ABC):
    """Abstract base class for all types in RDSL."""
    pass


################################################################################
#                                                                              #
# Archive
#                                                                              #
################################################################################

@dataclass
class Archive(DslType):
    """Archive type for RDSL."""

    name: str
    path: Path


################################################################################
#                                                                              #
# File
#                                                                              #
################################################################################

@dataclass
class File(DslType):
    """File type for RDSL."""

    name: str
    path: Path


################################################################################
#                                                                              #
# Repo
#                                                                              #
################################################################################

@dataclass
class Repo(DslType):
    """Repo type for RDSL."""

    path: Path


################################################################################
#                                                                              #
# Resource
#                                                                              #
################################################################################

@dataclass
class Resource(DslType):
    """Resource type for RDSL."""
    pass
