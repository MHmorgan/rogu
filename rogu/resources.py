"""types defines the types used in RDSL.

RESOURCE ACTIONS

 - Should raise ActionBlocked is blocked by a non-technical condition.

 - Should raise AppError if blocked by an expected technical condition.

 - Should not interact with the cache or history.
"""
import shutil
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

import log
import ugor
from errors import *


__all__ = [
    'Archive',
    'File',
    'Repo',
    'Resource',

    'cache_key',
    'delete',
    'exists',
    'expand_key',
    'get',
    'is_archive',
    'normalize_path',
]


class Resource:
    path: Path
    uri: str

    # CATEGORIES

    DEFAULT = 0

    # The install category indicates that a resource has been installed from
    # a remote source, and during syncing the local version should be updated.
    INSTALL = 1 << 0

    # The upload category indicates that a resource has been uploaded to Ugor
    # and during syncing the remote version should be updated.
    UPLOAD = 1 << 1

    # The sync category indicates that a resource should either be installed or
    # uploaded during update, depending on which version is newer.
    SYNC = INSTALL | UPLOAD

    # The git category indicates that a resource is a git repository and during
    # syncing the git repository should be updated.
    REPO = 1 << 3

    # The ignore category indicates that a resource should not be updated.
    IGNORE = 1 << 4

    # The category of the resource are used to determine how Rogu should
    # handle the resource during automatic updates.
    category: int = DEFAULT

    # Mapping of resource names to classes
    subclasses = {}

    def __init__(self, path, uri):
        if not uri:
            raise ValueError('Resource must have a uri.')
        if not path:
            raise ValueError('Resource must have a path.')
        self.uri = uri
        self.path = Path(normalize_path(path))

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.subclasses[cls.__name__] = cls

    def __hash__(self):
        """Hash the resource. The hash is constant between runs."""
        import zlib
        key = cache_key(path=self.path, uri=self.uri)
        return zlib.adler32(key.encode())

    def __eq__(self, other):
        if isinstance(other, Resource):
            return self.path == other.path and self.uri == other.uri
        return False

    @property
    def short_path(self):
        """Path as a string with home converted to ~ """
        home = str(Path.home())
        return str(self.path).replace(home, '~')

    @property
    def class_name(self):
        """Class name."""
        return self.__class__.__name__

    @property
    def local_hash(self):
        """Return a hash string of the resource locally.

        This is used to determine if the resource has changed locally.
        """
        if not self.path.exists():
            return ''
        return str(self.path.stat().st_mtime_ns)

    @property
    def key(self):
        """Resource's cache key."""
        return cache_key(path=self.path, uri=self.uri)

    @property
    def short_key(self):
        """Short version of resource's cache key."""
        return self.key[:10]

    def encode(self, encoding='utf-8', **kwargs):
        """Encode the resources cache key into bytes.

        This is a sneaky way to use resource objects as Shelve keys.
        Officially the keys must be strings, but since it internally
        encodes the keys to bytes, we can just encode the resource
        (note that the resource must also be hashable).
        """
        return self.key.encode(encoding=encoding)

    # ------------------------------------------------------
    # DISPLAY

    def __str__(self):
        return f'{self.class_name}:{self.short_key}'

    def __repr__(self):
        uri = self.uri
        path = self.short_path
        return f'<{self.class_name} {path=!r} {uri=!r}>'

    def __format__(self, format_spec):
        if format_spec == 'U':
            return self.uri
        if format_spec == 'P':
            return self.short_path
        if format_spec == 'K':
            return self.short_key
        if format_spec == 'C':
            return self.class_name
        if format_spec == 'H':
            return self.local_hash
        return str(self)


# ------------------------------------------------------------------------------
# ARCHIVE

class Archive(Resource):  # TODO
    """An archive object for RDSL.

    The archive path must be a directory.

    Manages reading and writing of archives, with compression, and other
    File functionality.
    """

    last_etag = None
    last_modified = None

    extensions = [
        ext
        for _, exts, _ in shutil.get_unpack_formats()
        for ext in exts  # List comprehension flat-mapping
    ]

    def __init__(self, path, uri, **kwargs):
        log.debug(f'Creating Archive of {path=!r} {uri=!r}')
        super().__init__(path, uri)

        # Make sure the path is a directory
        ex = self.path.exists()
        if ex and not self.path.is_dir():
            raise ValueError('Archive path must be a directory.')

    def refresh_metadata(self):
        """Refresh the metadata of the archive."""
        exists_ = self.path.exists()

        # Handle deleted/moved files
        if not exists_ and self.category:
            log.debug(f'{self.short_path} is deleted/moved - updating metadata.')
            self.category = Resource.DEFAULT
            self.last_etag = ''
            self.last_modified = ''


# ------------------------------------------------------------------------------
# FILE

class File(Resource):
    """A custom file object for RDSL.

    The file path must be a file.
    """

    last_etag = None
    last_modified = None

    def __init__(self, path, uri, **kwargs):
        log.debug(f'Creating File of {path=!r} {uri=!r}')
        super().__init__(path, uri)

        # Make sure the path is a file
        ex = self.path.exists()
        if ex and not self.path.is_file():
            raise ValueError('File path must be a file.')

    def refresh_metadata(self):
        """Refresh the metadata of the file."""
        exists_ = self.path.exists()

        # Handle deleted/moved files
        if not exists_ and self.category:
            log.debug(f'{self.short_path} is deleted/moved - updating metadata.')
            self.category = Resource.DEFAULT
            self.last_etag = None
            self.last_modified = None

    def install(self, mode=None, force=False, **kwargs):
        """Install the file to its path from the uri.

        :return: a ``Result``.
        """
        if force:
            log.debug(f'Forcing install.')

        if urlparse(self.uri).scheme != '':
            raise ActionBlocked(f'Invalid Ugor URI: {self.uri!r}')

        try:
            file = ugor.get(
                self.uri,
                etag=self.last_etag if not force else None,
                modified=self.last_modified if not force else None,
            )
        except UgorError404 as e:
            raise ActionBlocked(f'Ugor file {self.uri!r} not found') from e

        if file is None:
            raise ActionBlocked(f'{self.short_path} is already up-to-date')

        self.last_etag = file.last_etag
        self.last_modified = file.last_modified

        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True)
        self.path.write_bytes(file.content)
        if mode:
            self.path.chmod(mode)

    def upload(self, force=False, **kwargs):
        """Upload the file to Ugor."""

        if force:
            log.debug(f'Forcing upload.')

        if not self.path.exists():
            raise ActionBlocked(f'{self.short_path} does not exist')

        if urlparse(self.uri).scheme != '':
            raise ActionBlocked(f'Invalid Ugor URI: {self.uri!r}')

        # Don't overwrite existing ugor files on first upload
        if not self.last_etag and ugor.exists(self.uri) and not force:
            raise ActionBlocked(f'ugor file {self.uri!r} already exists')

        file, created = ugor.put(
            self.path.read_bytes(),
            name=self.uri,
            force=force,
            **{
                'last_etag': self.last_etag,
                'last_modified': self.last_modified,
            }
        )
        self.last_etag = file.last_etag
        self.last_modified = file.last_modified


# ------------------------------------------------------------------------------
# REPO

class Repo(Resource):  # TODO
    """A git repo object for RDSL."""

    def __init__(self, path, uri, **kwargs):
        log.debug(f'Creating Repo of {path=!r} {uri=!r}')
        super().__init__(path, uri)

        # Make sure the path is a directory
        ex = self.path.exists()
        if ex and not self.path.is_dir():
            raise ValueError('Repo path must be a directory.')


# ------------------------------------------------------------------------------
# CACHE INTERFACE

@cache
def cache_key(path, uri):
    """Get a cache key for a resource.

    uri must be a string.
    path must be a string or a Path object, and is always normalized.

    Returns a hash string.
    """
    import hashlib

    assert isinstance(path, (str, Path))
    assert isinstance(uri, str)

    path = normalize_path(path)

    # Two-letter key prefix
    base = ord('A')
    mod = ord('Z') - base + 1
    x = chr(base + (len(path) % mod))
    y = chr(base + (len(uri) % mod))

    # SHA1 hash of path and uri
    h = hashlib.sha1()
    h.update(path.encode())
    h.update(uri.encode())
    dig = h.hexdigest()

    return f'{x}{y}{dig}'


def expand_key(key):
    """Expand a partial cache key to a full key.

    Unless exactly one match is found, it raises ValueError.
    """
    from cache import resources
    matches = [k for k in resources if k.startswith(key)]
    if len(matches) > 1:
        raise ValueError(f'Key {key} is ambiguous.')
    elif len(matches) == 0:
        raise ValueError(f'Key {key} does not match any resources.')
    return matches.pop()


def exists(path, uri):
    """Check if a resource exists in the cache."""
    from cache import resources
    return cache_key(path=path, uri=uri) in resources


def get(path, uri):
    """Get a resource from the cache.

    If safe is False it raises ResourceNotFound if the resource is not found,
    otherwise it returns None.
    """
    from cache import resources
    from errors import ResourceNotFound

    if r := resources.get(cache_key(path=path, uri=uri)):
        return r
    raise ResourceNotFound(path, uri)


def delete(path, uri):
    """Delete a resource from the cache."""
    from cache import resources

    key = cache_key(path=path, uri=uri)
    if key in resources:
        del resources[key]


# ------------------------------------------------------------------------------
# UTILS

def is_archive(path):
    """Check if a path is an archive based on its extension."""
    if isinstance(path, Path):
        ext = ''.join(path.suffixes)
        return ext in Archive.extensions
    if isinstance(path, str):
        return any(path.endswith(ext) for ext in Archive.extensions)
    raise TypeError('path must be a string or a Path.')


def normalize_path(path):
    """Normalize a path.

    Returns a canonical path with expanded user and environment variables.
    """
    from os.path import expanduser, expandvars, realpath
    return realpath(expanduser(expandvars(path)))
