"""rdsl module implements the domain specific language used to automate
Rogu's tasks.

rdsl has no import side effects, and can be imported globally.

The language in abbreviated as RDSL.
"""

import os
from contextlib import AbstractContextManager

import log
from errors import AppError, ResourceNotFound
from resources import (
    Archive,
    File,
    Repo,
    Resource,
    is_archive
)


# TODO __all__


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

    Recording functions must return a tuple (ok, msg).
    """
    import history
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        assert isinstance(args[0], Resource)
        ok, msg = f(*args, **kwargs)
        history.record(f.__name__, args[0], ok, msg)
        return ok, msg

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
# RESOURCE INTERACTION

def fetch(path, uri, **kwargs):
    """Fetch/create a resource.

    If the resource is stored (cached) locally, it will be returned.
    Otherwise, the resource type is determined and a new resource is returned.

    Unused keyword arguments are passed to the resource constructor.

    :param path: local resource path
    :param uri: remote resource uri
    :keyword type: force the resource type (File/Archive/Repo)
    :return: a ``Resource`` instance
    """
    import resources
    from os.path import isdir, isfile

    type_ = kwargs.pop('type', None)
    cls = resources.Resource.subclasses.get(type_)

    # Stored resource
    try:
        r = resources.get(path, uri)
    except ResourceNotFound:
        pass
    else:
        log.debug(f'Found stored resource: {r}')
        if cls and not isinstance(r, cls):
            raise AppError(f'expected {type_} resource (forced), got {r.class_name}')
        return r

    # Forced resource type
    if cls:
        log.debug(f'Forced resource type: {type_}')
        return cls(path, uri)

    # Determine resource type
    if isfile(path):
        return File(path, uri, **kwargs)
    if uri.endswith('.git'):
        return Repo(path, uri, **kwargs)
    elif is_archive(uri) or isdir(path):
        return Archive(path, uri, **kwargs)
    else:
        return File(path, uri, **kwargs)


@need_resource
@refresh_resource
@recording
def update(resource, **kwargs):  # TODO
    """Update a resource.

    This may include installing updates, uploading new versions,
    syncing git repositories, etc.

    :param resource: a ``Resource`` instance
    :keyword force: force update even if the resource has local changes
    :return: a tuple (ok, msg). ``ok=True`` means the resource was updated.
    """
    log.info(f'Updating {resource}...')

    if is_ignored(resource):
        return False, f'Not updated: {resource.class_name} is ignored'

    if hasattr(resource, 'update'):
        return resource.update(**kwargs)

    if is_synced(resource):
        return sync(resource, **kwargs)
    elif is_installed(resource):
        return install(resource, **kwargs)
    elif is_uploaded(resource):
        return upload(resource, **kwargs)

    raise AppError(f"don't know how to update {resource}")


@need_resource
@refresh_resource
@recording
def install(resource, **kwargs):
    """Install a resource.

    *resource* is installed from its remote location to its local path.

    Handles file modes, decoding, unarchiving, repo cloning, etc.

    :param resource: a ``Resource`` instance
    :keyword force: force installation even if the resource has local changes
    :return: a tuple (ok, msg). ``ok=True`` means the resource was installed.
    """
    log.info(f'Installing {resource}...')

    # Don't install if the resource has local changes
    force = kwargs.get('force', False)
    if is_modified(resource, action='install') and not force:
        return False, 'Not installed: The resource has local changes.'

    # The resource must be installable
    if not hasattr(resource, 'install'):
        msg = f'cannot install {resource}: install() not implemented.'
        raise AppError(msg)

    log.debug(f'Installing {resource} from {resource.uri!r}')
    resource.category |= Resource.INSTALL
    return resource.install(**kwargs)


@need_resource
@refresh_resource
@recording
def upload(resource, **kwargs):
    """Upload a resource to Ugor.

    :param resource: a ``Resource`` instance
    :keyword force: force upload even if the resource has no local changes
    :return: a tuple (ok, msg). ``ok=True`` means the resource was uploaded.
    """
    log.info(f'Uploading {resource}...')

    # Don't upload if the resource has no local changes
    force = kwargs.get('force', False)
    if not is_modified(resource, action='upload') and not force:
        return False, 'Not uploaded: The resource has no local changes.'

    # The resource must be uploadable
    if not hasattr(resource, 'upload'):
        msg = f'cannot upload {resource}: upload() not implemented'
        raise AppError(msg)

    log.debug(f'Uploading {resource} to {resource.uri!r}')
    resource.category |= Resource.UPLOAD
    return resource.upload(**kwargs)


@need_resource
@refresh_resource
@recording
def sync(resource, **kwargs):  # TODO
    """Synchronise a resource. Sync is like a combination of install
    and upload.

    :param resource: a ``Resource`` instance
    :return: a tuple (ok, msg). ``ok=True`` means the resource was synced.
    """
    log.info(f'Synchronising {resource}...')

    # The resource must be installable and uploadable
    if not (hasattr(resource, 'install') and hasattr(resource, 'upload')):
        raise AppError(f'cannot sync {resource}: install() or upload() not implemented')

    log.debug(f'Synchronising {resource} with {resource.uri!r}')
    resource.category |= Resource.SYNC

    # Try to upload first
    ok, msg = upload(resource, **kwargs)
    log.info(msg)
    if ok:
        return True, f'Synced by upload.'

    # If upload failed, try to install
    ok, msg = install(resource, **kwargs)
    log.info(msg)
    if ok:
        return True, f'Synced by install.'

    return False, f'Not synced.'


@need_resource
@recording
def move(resource, path):
    """Move a resource locally.

    :param resource: a ``Resource`` instance
    :param path: the new local path
    :return: a tuple (ok, msg). ``ok=True`` means the resource was moved.
    """
    import cache
    import resources
    import shutil
    from pathlib import Path

    new_key = resources.cache_key(path=path, uri=resource.uri)
    old_path = resource.short_path

    # Check if a resource with the same path and uri already exists
    # XXX Could this be automatically handled?
    if new_key in cache.resources:
        return False, f'Not moved: Target resource already exists: {new_key}'

    path = shutil.move(str(resource.path), path)
    resource.path = Path(resources.normalize_path(path))
    return True, f'Moved {old_path} to {resource.short_path}'


@need_resource
@recording
def delete(resource, local=False, remote=True, force=False):
    """Remove a resource.

    :param resource: a ``Resource`` instance
    :param local: remove the local copy if ``True``
    :param remote: remove the Ugor file from server if ``True``
    :param force: force removal of Ugor file if ``True``
    """
    import ugor
    import cache
    import shutil

    msg = f'Removed {resource.uri} from '

    # Remove ugor file from server
    if is_ugor(resource) and remote:
        etag = getattr(resource, 'etag', None)
        modified = getattr(resource, 'modified', None)
        ugor.delete(
            name=resource.uri,
            etag=etag,
            modified=modified,
            force=force,
        )
        msg += 'Ugor; '

    # Delete local copy
    if local:
        if resource.path.exists():
            if resource.path.is_dir():
                shutil.rmtree(resource.path, ignore_errors=True)
            else:
                os.remove(resource.path)
            msg += 'local disk; '

    del cache.resources[resource]
    return True, msg + 'cache.'


# ------------------------------------------------------------------------------
# RESOURCE SUPPORT

@need_resource
def store(resource):
    """Store a resource in cache."""
    import cache
    cache.resources[resource] = resource


@need_resource
def exists(resource):
    """Check if a resource exists."""
    assert isinstance(resource, Resource)
    return resource.path.exists()


@need_resource
def is_ignored(resource):
    """Check if a resource is ignored."""
    return bool(resource.category & Resource.IGNORE)


@need_resource
def is_installed(resource):
    """Check if a resource is installed."""
    return bool(resource.category & Resource.INSTALL)


@need_resource
def is_uploaded(resource):
    """Check if a resource is updated."""
    return bool(resource.category & Resource.UPLOAD)


@need_resource
def is_synced(resource):
    """Check if a resource is synced."""
    return (resource.category & Resource.SYNC) == Resource.SYNC


@need_resource
def is_repo(resource):
    """Check if a resource is a git repository."""
    return bool(resource.category & Resource.REPO)


@need_resource
def is_modified(resource, action=None):
    """Check if a resource has local changes since last recorded history.

    If there are history entries for the resource, but the resource path
    does not exist, it is considered modified.
    If there are no history entries for the resource it is considered unmodified
    if it doesn't exist locally.
    """
    import history

    try:
        latest = next(
            entry
            for entry in history.resource_entries(resource)
            if not action or entry.action == action
        )
    except StopIteration:
        return exists(resource)
    else:
        return latest.local_hash != resource.local_hash or not exists(resource)


@need_resource
def is_ugor(resource):
    """Check if a resource is an Ugor resource."""
    from urllib.parse import urlparse
    return urlparse(resource.uri).scheme == ''
