"""rdsl module implements the domain specific language used to automate
Rogu's tasks.

RDSL RESOURCE ACTIONS

 - Are responsible for managing resource cache and history.

 - Should always return a Result object.
"""

import os
from contextlib import AbstractContextManager

from errors import *
from resources import (
    Archive,
    File,
    Resource,
    Release,
)
from result import Result, Ok, Fail
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
    'is_modified',
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


def recording(f):
    """Decorator to add resource history recording to a function.

    Recording functions must return a ``Result``.
    """
    import history
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        assert isinstance(args[0], Resource)
        res = f(*args, **kwargs)
        assert isinstance(res, Result)
        history.record(f.__name__, args[0], res.success, res.message)
        return res

    return wrapper


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

def fetch(path, uri, **kwargs):
    """Fetch/create a resource.

    If the resource is stored (cached) locally, it will be returned.
    Otherwise, the resource type is determined and a new resource is returned.

    Unused keyword arguments are passed to the resource constructor.

    :param path: local resource path
    :param uri: remote resource uri
    :param kwargs: keyword arguments passed to the resource constructor
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
        return File(path, uri, **kwargs)
    if parsed.scheme == 'ugor' and parsed.netloc == 'archive':
        return Archive(path, uri, **kwargs)
    if parsed.scheme == 'release':
        return Release(path, uri, **kwargs)

    raise AppError(f'cannot determine resource type: {path!r} {uri!r}')


@need_resource
@refresh_resource
@recording
def update(r):
    """Update a resource.

    This may include installing updates, uploading new versions,
    syncing git repositories, etc.

    :param r: a ``Resource`` instance
    :return: a ``Result`` instance
    """
    debug(f'Updating {r} of category 0b{r.category:b}')

    if is_ignored(r):
        return Fail(f'not updated: {r.class_name} is ignored')

    if hasattr(r, 'update'):
        return r.update()

    if is_synced(r):
        return sync(r)
    elif is_installed(r):
        return install(r)
    elif is_uploaded(r):
        return upload(r)

    uri = r.uri
    path = r.path
    raise AppError(f"don't know how to update {r} {path=!r} {uri=!r}")


@need_resource
@refresh_resource
@recording
def install(r, force=False):
    """Install a resource.

    *resource* is installed from its remote location to its local path.

    :param r: a ``Resource`` instance
    :param force: force installation even if the resource has local changes
    :return: a ``Result`` instance
    """
    debug(f'Installing {r!r}')

    # The resource must be installable
    if not hasattr(r, 'install'):
        msg = f'cannot install {r}: install() not implemented.'
        raise AppError(msg)

    # Don't install if the resource has local changes
    if is_modified(r) and exists(r) and not force:
        return Fail(f'not installed: {r} has local changes')

    r.category |= Resource.INSTALL
    try:
        r.install(force=force)
    except ActionBlocked as e:
        return Fail(f'not installed: {e}')
    return Ok(f'installed {r:U}')


@need_resource
@refresh_resource
@recording
def upload(r, force=False):
    """Upload a resource to Ugor.

    :param r: a ``Resource`` instance
    :param force: force upload even if the resource has no local changes
    :return: a ``Result`` instance
    """
    debug(f'Uploading {r!r}')

    # The resource must be uploadable
    if not hasattr(r, 'upload'):
        msg = f'cannot upload {r}: upload() not implemented'
        raise AppError(msg)

    # Don't upload if the resource has no local changes
    if is_modified(r) is False and not force:
        return Fail(f'not uploaded: {r} has no local changes')

    r.category |= Resource.UPLOAD
    try:
        r.upload(force=force)
    except ActionBlocked as e:
        return Fail(f'not uploaded: {e}')
    return Ok(f'uploaded {r:P}')


@need_resource
@refresh_resource
@recording
def sync(r):
    """Synchronise a resource. Sync is like a combination of install
    and upload.

    :param r: a ``Resource`` instance
    :return: a ``Result`` instance
    """
    debug(f'Synchronising {r!r}')

    # The resource must be installable and uploadable
    if not (hasattr(r, 'install') and hasattr(r, 'upload')):
        msg = f'cannot sync {r}: install() or upload() not implemented'
        return Fail(msg)

    r.category |= Resource.SYNC

    res = Ok()

    # Try to upload first
    if is_modified(r) is not False:
        try:
            r.upload()
        except ActionBlocked as e:
            res += f'not uploaded: {e}'
        else:
            return res(f'synced by uploading {r:P}')
    else:
        res += 'not uploaded: no local changes'

    # If upload failed, try to install
    if not is_modified(r) or not exists(r):
        try:
            r.install()
        except ActionBlocked as e:
            res += f'not installed: {e}'
        else:
            return res(f'synced by installing {r:U}')
    else:
        res += 'not installed: has local changes'

    return res + Fail('not synced')


@need_resource
@recording
def move(r, path):
    """Move a resource locally.

    :param r: a ``Resource`` instance
    :param path: the new local path
    :return: a ``Result`` instance
    """
    import cache
    import resources
    import shutil
    from pathlib import Path

    new_key = resources.cache_key(path=path, uri=r.uri)
    old_key = r.key
    old_path = r.short_path

    # Check if a resource with the same path and uri already exists
    # XXX Could this be automatically handled?
    if new_key in cache.resources:
        msg = f'not moved: target resource already exists: {new_key}'
        return Fail(msg)

    path = shutil.move(str(r.path), path)
    r.path = Path(resources.normalize_path(path))

    del cache.resources[old_key]
    del cache.modified[old_key]
    store(r)

    return Ok(f'moved {old_path} to {r.short_path}')


@need_resource
@recording
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

    res = Ok()

    # Remove ugor file from server
    if is_ugor(r) and remote:
        ugor.delete(
            name=r.uri,
            etag=getattr(r, 'last_etag', None),
            modified=getattr(r, 'last_modified', None),
            force=force,
        )
        res += 'deleted Ugor file'

    # Delete local copy
    if local:
        if r.path.exists():
            if r.path.is_dir():
                shutil.rmtree(r.path, ignore_errors=True)
            else:
                os.remove(r.path)
            res += 'deleted local copy'
        else:
            res += 'no local copy to delete'

    del cache.resources[r]
    del cache.modified[r]
    return res('deleted from cache')


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
    cache.modified[r] = r.local_hash


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
def is_modified(r):
    """Check if a resource has local changes since last recorded history.

    If there are history entries for the resource, but the resource path
    does not exist, it is considered modified.
    If there are no history entries for the resource it is considered unmodified
    if it doesn't exist locally.

    TODO Cleanup is_modified usage
    """
    import cache

    if r in cache.modified:
        return cache.modified[r] != r.local_hash
    return None


@need_resource
def is_ugor(resource):
    """Check if a resource is an Ugor resource."""
    from urllib.parse import urlparse
    return urlparse(resource.uri).scheme == 'ugor'
