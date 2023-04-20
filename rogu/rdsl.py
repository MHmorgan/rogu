"""rdsl module implements the domain specific language used to automate
Rogu's tasks.

RDSL RESOURCE ACTIONS

 - Are responsible for managing resource cache and history.
"""

import os
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Union

from errors import *
from resources import (
    Archive,
    File,
    Resource,
    Release,
)
from ui import *

__all__ = [
    'chdir',
    'fetch',
    'update',
    'install',
    'upload',
    'sync',
    'move',
    'delete',
    'store',

    'exists',
    'is_ignored',
    'is_installed',
    'is_uploaded',
    'is_synced',
    'is_ugor',
]


def need_resource(f):
    """Decorator to check that the first argument is a Resource."""
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not isinstance(args[0], Resource):
            raise TypeError(f'{type(args[0])} is not a Resource')
        return f(*args, **kwargs)

    return wrapper


def refresh_resource(f):
    """Decorator to refresh the resource metadata."""
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if hasattr(args[0], 'refresh_metadata'):
            args[0].refresh_metadata()
        return f(*args, **kwargs)

    return wrapper


def fail(msg, cause=None, /):
    if cause:
        raise AppError(msg) from cause
    raise AppError(msg)


def blocked(msg, cause=None, /):
    if cause:
        raise ActionBlocked(msg) from cause
    raise ActionBlocked(msg)


def run(o):
    """Run the given object as a RDSL script.

    The object can be a string (source code), a file object,
    a Path object, or a code object.
    """
    pass  # TODO implement run RDSL script


class chdir(AbstractContextManager):
    """Change work directory.

    May be used as a context manager or function.
    """

    def __init__(self, path):
        self._old_cwd = [os.getcwd()]
        os.chdir(path)

    def __exit__(self, *excinfo):
        os.chdir(self._old_cwd.pop())


# ------------------------------------------------------------------------------
# RESOURCE ACTIONS

def fetch(path: Union[Path, str], uri: str) -> Resource:
    """Fetch/create a resource.

    If the resource is stored (cached) locally, it will be returned.
    Otherwise, the resource type is determined and a new resource is returned.

    Unused keyword arguments are passed to the resource constructor.

    :param path: local resource path
    :param uri: remote resource uri
    :return: a ``Resource`` instance
    """
    import resources
    from urllib.parse import urlparse

    # Stored resource
    try:
        r = resources.get(path, uri)
    except ResourceNotFound:
        pass
    else:
        debug(f'Found stored resource: {r}')
        return r

    # Determine resource type
    parsed = urlparse(uri)
    if parsed.scheme == 'ugor' and parsed.netloc == 'file':
        return File(path, uri)
    if parsed.scheme == 'ugor' and parsed.netloc == 'archive':
        return Archive(path, uri)
    if parsed.scheme == 'release':
        return Release(path, uri)

    fail(f'cannot determine resource type: {path!r} {uri!r}')


@need_resource
@refresh_resource
def update(r):
    """Update a resource.

    This may include installing updates, uploading new versions,
    syncing git repositories, etc.

    :param r: a ``Resource`` instance
    """
    debug(f'Updating {r} of category 0b{r.category:b}')

    if is_ignored(r):
        blocked(f'not updated: {r.class_name} is ignored')

    if hasattr(r, 'update'):
        r.update()
    elif is_synced(r):
        sync(r)
    elif is_installed(r):
        install(r)
    elif is_uploaded(r):
        upload(r)
    else:
        uri = r.uri
        path = r.path
        fail(f"don't know how to update {r} {path=!r} {uri=!r}")


@need_resource
@refresh_resource
def install(r, force=False):
    """Install a resource.

    *resource* is installed from its remote location to its local path.

    :param r: a ``Resource`` instance
    :param force: force installation even if the resource has local changes
    """
    debug(f'Installing {r!r}')

    # The resource must be installable
    if not hasattr(r, 'install'):
        fail(f'cannot install {r}: install() not implemented.')

    if hasattr(r, 'divergence') and exists(r) and not force:
        d = r.divergence()
        debug(f'Install divergence: {d}')
        if d == 0:
            verbose(f'{r} is up-to-date')
            return
        elif d > 0:
            blocked('not installed: has new local changes')

    r.category |= Resource.INSTALL
    r.install(force=force)


@need_resource
@refresh_resource
def upload(r, force=False):
    """Upload a resource to Ugor.

    :param r: a ``Resource`` instance
    :param force: force upload even if the resource has no local changes
    :return: a ``Result`` instance
    """
    debug(f'Uploading {r!r}')

    # The resource must be uploadable
    if not hasattr(r, 'upload'):
        fail(f'cannot upload {r}: upload() not implemented')

    if hasattr(r, 'divergence') and not force:
        d = r.divergence()
        debug(f'Upload divergence: {d}')
        if d == 0:
            verbose(f'{r} is up-to-date')
            return
        elif d < 0:
            fail('not uploaded: has new remote changes')

    r.category |= Resource.UPLOAD
    r.upload(force=force)


@need_resource
@refresh_resource
def sync(r):
    """Synchronise a resource. Sync is like a combination of install
    and upload.

    :param r: a ``Resource`` instance
    """
    debug(f'Synchronising {r!r}')

    # The resource must be installable and uploadable
    if not hasattr(r, 'install'):
        fail(f'cannot sync {r}: install() not implemented')
    if not hasattr(r, 'upload'):
        fail(f'cannot sync {r}: upload() not implemented')
    if not hasattr(r, 'divergence'):
        fail(f'cannot sync {r}: divergence() not implemented')

    r.category |= Resource.SYNC

    d = r.divergence()
    debug(f'Sync divergence: {d}')

    if d in (2, -2):
        blocked('not synced: has new local and remote changes')

    if d == 1:
        debug(f'Uploading resource...')
        r.upload()
        return

    elif d == -1:
        debug(f'Installing resource...')
        r.install()


@need_resource
def move(r, path):
    """Move a resource locally.

    :param r: a ``Resource`` instance
    :param path: the new local path
    """
    import cache
    import resources
    import shutil
    from pathlib import Path

    new_key = resources.cache_key(path=path, uri=r.uri)
    old_key = r.key

    # Check if a resource with the same path and uri already exists
    # XXX Could this be automatically handled?
    if new_key in cache.resources:
        fail(f'not moved: target resource already exists: {new_key}')

    path = shutil.move(str(r.path), path)
    r.path = Path(resources.normalize_path(path))

    del cache.resources[old_key]
    del cache.modified[old_key]
    store(r)


@need_resource
def delete(r, local, remote, force=False):
    """Remove a resource.

    :param r: a ``Resource`` instance
    :param local: remove the local copy if ``True``
    :param remote: remove the Ugor file from server if ``True``
    :param force: force removal of Ugor file if ``True``
    """
    import ugor
    import cache
    import shutil

    # Remove ugor file from server
    if is_ugor(r) and remote:
        ugor.delete(
            name=r.name,
            etag=getattr(r, 'last_etag', None),
            modified=getattr(r, 'last_modified', None),
            force=force,
        )
        verbose('Deleted Ugor file')

    # Delete local copy
    if local:
        if r.path.exists():
            if r.path.is_dir():
                shutil.rmtree(r.path, ignore_errors=True)
            else:
                os.remove(r.path)
            verbose('Deleted local copy')
        else:
            verbose('No local copy to delete')

    del cache.resources[r]
    del cache.modified[r]
    verbose('Deleted from cache')


# ------------------------------------------------------------------------------
# RESOURCE SUPPORT

@need_resource
def store(r):
    """Store a resource in cache.

    This should be the only way to store a resource in cache.

    :param r: a ``Resource`` instance
    """
    import cache
    cache.resources[r] = r
    cache.modified[r] = r.path_hash


@need_resource
def exists(r):
    """Check if a resource exists."""
    assert isinstance(r, Resource)
    return r.path.exists()


@need_resource
def is_ignored(r):
    """Check if a resource is ignored."""
    return bool(r.category & Resource.IGNORE)


@need_resource
def is_installed(r):
    """Check if a resource is installed."""
    return bool(r.category & Resource.INSTALL)


@need_resource
def is_uploaded(r):
    """Check if a resource is updated."""
    return bool(r.category & Resource.UPLOAD)


@need_resource
def is_synced(r):
    """Check if a resource is synced."""
    return (r.category & Resource.SYNC) == Resource.SYNC


@need_resource
def is_ugor(resource):
    """Check if a resource is an Ugor resource."""
    from urllib.parse import urlparse
    return urlparse(resource.uri).scheme == 'ugor'
