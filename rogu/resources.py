"""The resource objects - the core of Rogu"""

import abc
import shutil
import hashlib
import os
import re
from functools import cache
from pathlib import Path
from typing import Union, Optional
from urllib.parse import urlparse

import arrow
import ugor
from errors import *
from ui import *

__all__ = [
    'Archive',
    'File',
    'Resource',
    'Release',

    'cache_key',
    'expand_key',
    'get',
    'normalize_path',
]


class Resource(abc.ABC):
    """Resource is the base class for all resources, the core of Rogu.

    All resources have a ``path`` and an ``uri``, which uniquely identifies
    the resource.

    The behavior of resources are heavily reliant on duck-typing, and which
    actions a resource supports is determined by the presence of the methods
    for an action. The following methods are supported:

    ``install(force)``
        install the resource.

    ``upload(force)``
        upload the resource.

    ``delete(force)``
        delete the resource.

    ``divergence()``
        returns an integer indicating the divergence between the path and uri:
        0 - path and uri content are identical;
        1 - path is newer;
        2 - path is newer but uri has diverged;
        -1 - uri is newer;
        -2 - uri is newer but path has diverged.

    ``refresh_metadata()``
        refresh the metadata of the resource.

    :param path: the path to the resource.
    :param uri: the uri of the resource.
    """
    path: Path
    uri: str

    # CATEGORIES

    DEFAULT = 0

    # The install category indicates that a resource has been installed from
    # the uri source, and during syncing the path content should be updated.
    INSTALL = 1 << 0

    # The upload category indicates that a resource has been uploaded to Ugor
    # and during syncing the remote version should be updated.
    UPLOAD = 1 << 1

    # The sync category indicates that a resource should either be installed or
    # uploaded during update, depending on which version is newer.
    SYNC = INSTALL | UPLOAD

    # The ignore category indicates that a resource should not be updated.
    IGNORE = 1 << 4

    # The category of the resource are used to determine how Rogu should
    # handle the resource during automatic updates.
    category: int = DEFAULT

    # Mapping of resource names to classes
    subclasses = {}

    def __init__(self, path: Union[Path, str], uri: str):
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
    def short_path(self) -> str:
        """Path as a string with home converted to ~ """
        home = str(Path.home())
        return str(self.path).replace(home, '~')

    @property
    def class_name(self) -> str:
        """Class name."""
        return self.__class__.__name__

    @property
    def path_hash(self) -> str:
        """Hash string of the resource locally.

        This is used to determine if the resource has changed locally.
        """
        if not self.path.exists():
            return ''

        h = hashlib.sha1()

        # If the resource is a file, just hash the file
        if self.path.is_file():
            h.update(self.path.read_bytes())
            return h.hexdigest()

        # Respect the first .gitignore encountered
        gitignore = None

        # If the resource is a directory, hash all files in the directory
        for root, dirs, files in os.walk(self.path):
            root = Path(root)

            if '.git' in root.parts:
                continue
            if gitignore and root.name in gitignore:
                continue

            if not gitignore and '.gitignore' in files:
                gitignore = root / '.gitignore'

            for file in files:
                if gitignore and file in gitignore:
                    continue
                p = root / file
                rel = os.path.relpath(p, self.path)
                h.update(p.read_bytes())
                # Hash path to detect renames
                h.update(rel.encode())

        return h.hexdigest()

    @property
    def path_modified(self) -> arrow.Arrow:
        """The time the resource was last modified locally.

        If the resource is a directory, the last modified time of any file
        in the directory is returned.
        """

        if not self.path.exists():
            return arrow.get(0)

        if self.path.is_file():
            return arrow.get(self.path.stat().st_mtime)

        # Respect the first .gitignore encountered
        gitignore = None
        time = arrow.get(0)

        # Find the last modified time of any file in the directory
        for root, dirs, files in os.walk(self.path):
            root = Path(root)

            if '.git' in root.parts:
                continue
            if gitignore and root.name in gitignore:
                continue

            if not gitignore and '.gitignore' in files:
                gitignore = root / '.gitignore'

            for file in files:
                if gitignore and file in gitignore:
                    continue
                p = root / file
                time = max(time, arrow.get(p.stat().st_mtime))

        return time

    @property
    def key(self):
        """Resource's cache key."""
        return cache_key(path=self.path, uri=self.uri)

    @property
    def short_key(self):
        """Short version of resource's cache key."""
        return self.key[:10]

    @property
    def name(self):
        """The name of the resource. This is only intended to be a human-friendly
        display name, and should not be used for anything else.

        May be overridden by subclasses.
        """
        return self.path.name

    def encode(self, encoding='utf-8', **kwargs):
        """Encode the resources cache key into bytes.

        This is a sneaky way to use resource objects as Shelve keys.
        Officially the keys must be strings, but since it internally
        encodes the keys to bytes, we can just encode the resource
        (note that the resource must also be hashable).
        """
        return self.key.encode(encoding=encoding)

    # DISPLAY

    def __str__(self):
        return f'{self.short_key}:{self.name}'

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
            return self.path_hash
        return str(self)


# ------------------------------------------------------------------------------
# UGOR RESOURCE

class _UgorResource(Resource):
    """A base resource for all resources which install or upload to Ugor.

    All subclasses must make sure ``self.name`` is set to the name of the
    Ugor file.
    """
    last_etag = None
    last_modified = None
    description = None

    def ugor_install(self, force: bool) -> Optional[bytes]:
        """Download this resource from Ugor.

        Handles etag and modified logic.

        :returns: the file content or None if it's up-to-date.
        """
        debug('..._UgorResource.ugor_install()')

        file = ugor.get(
            name=self.name,
            etag=self.last_etag if not force else None,
            modified=self.last_modified if not force else None,
        )

        if file is None:
            verbose(f'{self} is up-to-date')
            return None
        if file.description:
            self.description = file.description

        self.last_etag = file.last_etag
        self.last_modified = file.last_modified
        return file.content

    def ugor_upload(self, obj: Union[Path, bytes, str], force: bool):
        """Upload this resource to Ugor."""
        debug('..._UgorResource.ugor_upload()')

        file = ugor.put(
            obj=obj,
            name=self.name,
            force=force,
            **{
                'last_etag': self.last_etag,
                'last_modified': self.last_modified,
                'description': self.description,
                'tag2': 'Rogu',
                'data2': self.path_hash,
            }
        )
        self.last_etag = file.last_etag
        self.last_modified = file.last_modified

    def divergence(self) -> int:
        """Return the divergence between the path and uri content.

        :returns: an ``int`` indicating the divergence:
            0 - path and uri content are identical;
            1 - path is newer;
            2 - path is newer but uri has diverged;
            -1 - uri is newer;
            -2 - uri is newer but path has diverged.
        """
        debug('..._UgorResource.divergence()')

        try:
            header = ugor.get_header(self.name)
        except UgorError404:
            # If path exists it is newest
            return 1 if self.path.exists() else 0

        # If path does not exist, uri is newest
        if not self.path.exists():
            return -1

        old_etag = self.last_etag  # ETag at last install or upload
        new_etag = header.etag
        old_hash = header.data2  # Hash at last upload
        new_hash = self.path_hash
        uri_mod = arrow.get(header.modified)
        path_mod = self.path_modified

        # At this point we know both path and uri exist

        is_uploaded = old_hash is not None
        is_new = old_etag is None
        has_local_changes = old_hash != new_hash
        has_remote_changes = old_etag != new_etag

        # If this is a new resource, but both local and remote exist
        # they have diverged.
        if is_new:
            return -2 if uri_mod > path_mod else 2

        # If a resource has never been uploaded we don't know the last local
        # hash, so we can not know if it has diverged.
        # We can only assume that these resources will only ever be installed
        # from Ugor, and never uploaded.
        if not is_uploaded:
            return -1 if has_remote_changes else 0

        if has_local_changes and has_remote_changes:
            return -2 if uri_mod > path_mod else 2
        if has_local_changes and not has_remote_changes:
            return 1
        if not has_local_changes and has_remote_changes:
            return -1
        return 0


# ------------------------------------------------------------------------------
# ARCHIVE

class Archive(_UgorResource):
    """An archive object for RDSL.

    The archive path must be a directory.

    Manages reading and writing of archives, with compression, and other
    File functionality.
    """

    format = 'xztar'

    extensions = {
        fmt: ext[0]
        for fmt, ext, _ in shutil.get_unpack_formats()
    }

    def __init__(
            self,
            path: Union[Path, str],
            uri: str,
            description: str = None
    ):
        debug(f'Creating Archive of {path=!r} {uri=!r}')
        super().__init__(path, uri)
        self.description = description

        parsed = urlparse(uri)
        if m := re.search(r'format=(\w+)', parsed.query):
            self.format = m.group(1)
        if self.format not in self.extensions:
            raise ValueError(f'Invalid archive format: {self.format}')

    @property
    def name(self):
        """Archive name with extension. This is the Ugor name."""
        return self.base_name + self.extensions[self.format]

    @property
    def base_name(self):
        """Archive name without archive extension."""
        return urlparse(self.uri).path.lstrip('/')

    # RESOURCE ACTIONS

    def refresh_metadata(self):
        """Refresh the etag and modified values of the archive."""
        exists_ = self.path.exists()

        # Handle deleted/moved files
        if not exists_ and self.category:
            debug(f'{self.short_path} is deleted/moved - updating metadata.')
            self.category = Resource.DEFAULT
            self.last_etag = ''
            self.last_modified = ''

    def install(self, force: bool = False):
        """Install the archive to its path from the uri."""
        import cache
        debug('...Archive.install()')

        content = self.ugor_install(force)
        if content is None:
            return

        ftmp = cache.path(self.name)
        ftmp.write_bytes(content)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(ftmp, self.path)

    def upload(self, force: bool = False):
        """Upload the archive to Ugor."""
        import cache
        debug('...Archive.upload()')

        if not self.path.exists():
            raise ActionBlocked(f'{self.short_path} does not exist.')

        arch = Path(pack_archive(
            dst=cache.path(self.base_name),
            src=self.path,
            fmt=self.format,
        ))

        self.ugor_upload(arch, force)


# ------------------------------------------------------------------------------
# FILE

class File(_UgorResource):
    """A custom file object for RDSL.

    The file path must be a file.
    """

    def __init__(
            self,
            path: Union[Path, str],
            uri: str,
            description: str = None
    ):
        debug(f'Creating File of {path=!r} {uri=!r}')
        super().__init__(path, uri)
        self.description = description

    @property
    def name(self):
        """The Ugor file name."""
        return urlparse(self.uri).path.lstrip('/')

    def refresh_metadata(self):
        """Refresh the metadata of the file."""
        exists_ = self.path.exists()

        # Handle deleted/moved files
        if not exists_ and self.category:
            debug(f'{self.short_path} is deleted/moved - updating metadata.')
            self.category = Resource.DEFAULT
            self.last_etag = None
            self.last_modified = None

    def install(self, force: bool = False):
        """Install the file to its path from the uri."""
        debug('...File.install()')
        content = self.ugor_install(force)
        if content is None:
            return

        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True)
        if self.path.exists():
            backup = self.path.parent / f'.{self.path.name}~'
            shutil.copy(self.path, backup)
            debug(f'Backed up to {backup.name}')
        self.path.write_bytes(content)

    def upload(self, force: bool = False):
        """Upload the file to Ugor."""
        debug('...File.upload()')

        if force:
            debug(f'Forcing upload.')

        if not self.path.exists():
            raise ActionBlocked(f'{self.short_path} does not exist')

        self.ugor_upload(self.path, force)


# ------------------------------------------------------------------------------
# RELEASE

class Release(Resource):
    """A GitHub Release object for RDSL."""

    last_etag = None

    def __init__(self, path, uri):
        debug(f'Creating Release of {path=!r} {uri=!r}')
        super().__init__(path, uri)

    @property
    def github_url(self):
        """The GitHub URL of the release."""
        parsed = urlparse(self.uri)
        repo, user = parsed.netloc.split('@')
        file = parsed.path.lstrip('/')
        return f'https://github.com/{user}/{repo}/releases/latest/download/{file}'

    def divergence(self):
        """Return the divergence of the release.

        Returns:
            int: 0 if the release is up-to-date, 1 if the release is newer,
                -1 if the release is older, -2 if the release is newer and
                the local file is newer, and 2 if the release is older and
                the local file is older.
        """
        # Check if the release has changed
        import requests
        debug(f'...Release.divergence()')

        # A release can only ever be installed, and are not expected to be
        # modified locally. If it doesn't exist or haven't been installed
        # previously, the remote must be newest.
        if not self.path.exists() or not self.last_etag:
            return -1

        r = requests.head(self.github_url, allow_redirects=True)
        etag = r.headers.get('ETag')

        # If the ETag isn't available we must always assume the release
        # has changed.
        if etag is None:
            return -1

        return 0 if self.last_etag == etag else -1

    def install(self, force=False):
        """Install the release to its path from the uri.

        If the release file has an archive extension, it will be unpacked.
        If it has gz, bz2, or xz extension it will be decompressed.
        """
        import cache
        import requests
        debug(f'...Release.install()')

        url = self.github_url
        file = urlparse(url).path.lstrip('/')

        if self.path.exists():
            mode = self.path.stat().st_mode
        else:
            mode = None
        debug(f'File {mode=!r}')

        # Download the release
        r = requests.get(url, allow_redirects=True)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ActionBlocked(e)
        self.last_etag = r.headers.get('ETag')

        # Unpack/Decompress and install the release
        ftmp = cache.path(file)
        with ftmp.open('wb') as f:
            f.write(r.content)

        shutil.register_unpack_format('gzip', ['.gz'], unpack_gzip)
        shutil.register_unpack_format('bzip2', ['.bz2'], unpack_bzip2)
        shutil.register_unpack_format('xz', ['.xz'], unpack_xz)

        try:
            shutil.unpack_archive(ftmp, self.path)
            debug(f'Unpacked release to {self.path}')
        except shutil.ReadError:
            shutil.copy(ftmp, self.path)
            debug(f'Installed release to {self.path}')
        finally:
            if mode is not None and self.path.exists():
                self.path.chmod(mode)
            shutil.unregister_unpack_format('gzip')
            shutil.unregister_unpack_format('bzip2')
            shutil.unregister_unpack_format('xz')


# ------------------------------------------------------------------------------
# CACHE INTERFACE

@cache
def cache_key(path: Union[Path, str], uri: str) -> str:
    """Get a cache key for a resource.

    uri must be a string.
    path must be a string or a Path object, and is always normalized.

    Returns a hash string.
    """
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


def expand_key(key: str) -> str:
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


def get(path: Union[Path, str], uri: str) -> Resource:
    """Get a resource from the cache.

    If safe is False it raises ResourceNotFound if the resource is not found,
    otherwise it returns None.
    """
    from cache import resources
    from errors import ResourceNotFound

    if r := resources.get(cache_key(path=path, uri=uri)):
        return r
    raise ResourceNotFound(path, uri)


# ------------------------------------------------------------------------------
# UTILS

def normalize_path(path: Union[Path, str]) -> str:
    """Normalize a path.

    Returns a canonical path with expanded user and environment variables.
    """
    from os.path import expanduser, expandvars, realpath
    return realpath(expanduser(expandvars(path)))


class Gitignore:

    def __init__(self, path: Union[Path, str]):
        self.patterns = []

        for line in open(path):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            self.patterns.append(line)

    def __contains__(self, item: str):
        from fnmatch import fnmatch
        return any(fnmatch(item, pattern) for pattern in self.patterns)


def unpack_gzip(path, dest):
    """Unpack a gzip file to a destination."""
    import gzip
    with gzip.open(path, 'rb') as f:
        Path(dest).write_bytes(f.read())


def unpack_bzip2(path, dest):
    """Unpack a bzip2 file to a destination."""
    import bz2
    with bz2.open(path, 'rb') as f:
        Path(dest).write_bytes(f.read())


def unpack_xz(path, dest):
    """Unpack a xz file to a destination."""
    import lzma
    with lzma.open(path, 'rb') as f:
        Path(dest).write_bytes(f.read())


@cache
def pack_archive(dst, src, fmt):
    """Pack a directory to a destination.

    This is a wrapper around shutil.make_archive that caches the result.
    The goal of this function is to avoid repacking the same directory
    multiple times during a single run.

    :returns str: The path to the archive.
    """
    return shutil.make_archive(
        base_name=dst,
        format=fmt,
        root_dir=src,
    )
