"""
ugor handles the communication with the Ugor server.
"""
from dataclasses import dataclass
from functools import wraps

import click
import requests

import log
from errors import AppError, UgorError

__all__ = ['auth', 'get', 'put', 'delete', 'find', 'info', 'UgorFile']


def _ugor_error(f):
    """Decorator that converts HTTPError's into Ugor errors"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except requests.HTTPError as e:
            raise UgorError(e.response, str(e)) from e

    return wrapper


# -----------------------------------------------------------------------------
# Primary functions

@_ugor_error
def get(name, etag=None, modified=None):
    """Get a file from the Ugor server.

    Use etag and modified to check if the file is updated.
    Modified may be a string or an object with a isoformat() method
    (like datetime.datetime and arrow.Arrow).

    Return None if the file isn't updated.
    Raises UgorError404 if the file doesn't exist.
    """
    headers = {}
    if etag:
        headers['If-None-Match'] = etag
    if modified:
        if hasattr(modified, 'isoformat'):
            modified = modified.isoformat()
        headers['If-Modified-Since'] = modified

    url = _url(name)
    log.debug(f'GET {url!r}', *[f"{k}: {v!r}" for k, v in headers.items()])

    r = requests.get(url, auth=auth(), headers=headers)
    r.raise_for_status()
    if r.status_code == 304:
        return None
    return UgorFile.of_response(name, r)


@_ugor_error
def put(o, name='', use_pickle=False, force=False, **metadata):
    """Upload something to the Ugor server.

    If o is an UgorFile, it will be uploaded as is.
    The name and metadata parameters is ignored.

    If o is a Path it will be uploaded as a file.
    Default name is the path basename.

    If o is string/bytes and name is falsy, then it is assumed to be a file path.
    Default name is the path basename.

    If o is string/bytes and name is truthy, then it is assumed to be the
    content of a file.

    If o is a dict or list, it will be serialized as JSON before uploading.
    No default value for name.

    If o is an object with a read() method, then it will be read and uploaded
    as a file. Default name is o.name if it exists.

    If o is anything else, it will be pickled and uploaded.
    Default name is o.name if it exists.

    If use_pickle is True, o will be pickled and uploaded regardless of the type.
    No default value for name.

    If force is True, the file will be uploaded even if the ETag or Last-Modified
    preconditions fails.

    The metadata will be passed along to the UgorFile constructor.

    Returns a tuple (file, created), where file is the UgorFile that was uploaded,
    with new ETag and Last-Modified values, and created is True if the file was
    created, False if it was updated.

    Raises UgorError412 if any of the preconditions fails.
    Raises FileNotFoundError if o is a file path that doesn't exist.
    """
    import json
    import pickle
    from pathlib import Path
    from reprlib import repr  # Slightly prettier repr

    # Create file object from o
    if use_pickle:
        log.debug(f'Ugor put file: forced pickle of', repr(o))
        if not name:
            raise ValueError('name must be given if use_pickle is True')
        content = pickle.dumps(o)
        metadata.setdefault('mime_type', 'application/octet-stream')
        metadata.setdefault('encoding', 'pickle')
        file = UgorFile.of(name, content, **metadata)
    elif isinstance(o, UgorFile):
        log.debug('Ugor put file: from UgorFile', repr(o))
        file = o
    elif isinstance(o, Path):
        log.debug('Ugor put file: from path', repr(o))
        file = UgorFile.of_file(name or o.name, o, **metadata)
    elif isinstance(o, (str, bytes)) and not name:
        log.debug('Ugor put file: from path (string/bytes)', repr(o))
        file = UgorFile.of_file(Path(o).name, o, **metadata)
    elif isinstance(o, (str, bytes)) and name:
        log.debug('Ugor put file: with str/bytes content, named', repr(name))
        file = UgorFile.of(name, o, **metadata)
    elif isinstance(o, (dict, list)):
        log.debug('Ugor put file: with JSON content, from dict/list', repr(o))
        if not name:
            raise ValueError('name must be given if o is a dict/list')
        content = json.dumps(o).encode()
        metadata.setdefault('mime_type', 'application/json')
        file = UgorFile.of(name, content, **metadata)
    else:
        if hasattr(o, 'read') and callable(o.read):
            log.debug('Ugor put file: with content read from', repr(o))
            content = o.read()
        else:
            log.debug('Ugor put file: with pickled content from', repr(o))
            content = pickle.dumps(o)
        if name := (getattr(o, 'name', '') or name):
            file = UgorFile.of(name, content, **metadata)
        else:
            raise ValueError('name must be given if o has no name')

    headers = file.headers()
    if file.last_etag and not force:
        headers['If-Match'] = file.last_etag
    if file.last_modified and not force:
        headers['If-Unmodified-Since'] = file.last_modified

    url = _url(file.name)
    log.debug('PUT', url, *[f"{k}: {v!r}" for k, v in headers.items()])
    r = requests.put(url, auth=auth(), headers=headers, data=file.content)
    r.raise_for_status()

    try:
        file.last_etag = r.headers['ETag']
        file.last_modified = r.headers['Last-Modified']
    except KeyError as e:
        raise AppError(f'Ugor server did not return ETag and/or Last-Modified headers') from e

    if r.status_code == 201:
        log.debug('Ugor put: Created', file.name)
    elif r.status_code == 200:
        log.debug('Ugor put: Updated', file.name)
    return file, r.status_code == 201


@_ugor_error
def delete(name, force=False, etag=None, modified=None):  # TODO
    """Delete a file from the Ugor server"""
    headers = {}
    if etag and not force:
        headers['If-Match'] = etag
    if modified and not force:
        if hasattr(modified, 'isoformat'):
            modified = modified.isoformat()
        headers['If-Unmodified-Since'] = modified

    url = _url(name)
    log.debug('DELETE', url, *[f"{k}: {v!r}" for k, v in headers.items()])
    r = requests.delete(url, auth=auth(), headers=headers)
    r.raise_for_status()


@_ugor_error
def find(**params):  # TODO
    """Find files on the Ugor server with the given search parameters"""
    from config import ugor_url

    params = {k: v for k, v in params.items() if v is not None}
    log.debug('FIND', ugor_url, params)
    r = requests.request('FIND', ugor_url, auth=auth(), json=params)
    r.raise_for_status()
    return r.json()


@_ugor_error
def info():
    """Get information about the Ugor server"""
    from config import ugor_url

    log.debug('INFO', ugor_url)
    r = requests.request('INFO', ugor_url, auth=auth())
    r.raise_for_status()
    return r.json()


@_ugor_error
def exists(name):
    """Check if a file exists on the Ugor server"""
    url = _url(name)
    log.debug('HEAD', url)
    r = requests.head(url, auth=auth())
    if r.status_code == 404:
        return False
    r.raise_for_status()
    return True


# -----------------------------------------------------------------------------
# UgorFile

@dataclass
class UgorFile:
    """A file retrieved from the Ugor server"""

    name: str
    content: bytes
    mime_type: str = None
    encoding: str = None

    # The ETag and Last-Modified headers set by the server
    last_etag: str = None
    last_modified: str = None

    # Metadata
    description: str = None
    tag: str = None
    tag2: str = None
    tag3: str = None
    data: str = None
    data2: str = None
    data3: str = None
    data4: str = None
    data5: str = None

    def __post_init__(self):
        """Do some post-initialization work, normalizing data,
        guessing mime type and encoding, etc.
        """
        import mimetypes

        assert self.name and isinstance(self.name, str),\
            'name must be given and be a string'
        assert self.content and isinstance(self.content, bytes),\
            'content must be given and be bytes'

        # Guess mime type and encoding
        if not (self.mime_type and self.encoding):
            mime_type, encoding = mimetypes.guess_type(self.name)
            self.mime_type = self.mime_type or mime_type
            self.encoding = self.encoding or encoding

        # Convert datetime/Arrow objects to ISO strings
        if self.last_modified and hasattr(self.last_modified, 'isoformat'):
            self.last_modified = self.last_modified.isoformat()

    @classmethod
    def of(cls, name, content, **metadata):
        """Create an UgorFile from a name and content."""
        if isinstance(content, str):
            content = content.encode()
        elif not isinstance(content, bytes):
            raise TypeError('content must be a string or bytes')
        return cls(name=name, content=content, **metadata)

    @classmethod
    def of_response(cls, name, response: requests.Response):
        """Create a UgorFile from a response.

        This is based on the response of a GET request to Ugor, which is
        expected to always contain the ETag, Last-Modified and Content-Type
        headers.

        Raises AppError if the response is missing a required header.
        """
        try:
            return cls(
                name=name,
                content=response.content,
                last_etag=response.headers['ETag'],
                last_modified=response.headers['Last-Modified'],
                mime_type=response.headers['Content-Type'],
                encoding=response.headers.get('Content-Encoding'),
                description=response.headers.get('File-Description'),
                tag=response.headers.get('File-Tag'),
                tag2=response.headers.get('File-Tag2'),
                tag3=response.headers.get('File-Tag3'),
                data=response.headers.get('File-Data'),
                data2=response.headers.get('File-Data2'),
                data3=response.headers.get('File-Data3'),
                data4=response.headers.get('File-Data4'),
                data5=response.headers.get('File-Data5'),
            )
        except KeyError as e:
            raise AppError(f'Invalid Ugor response missing header {e}') from e

    @classmethod
    def of_file(cls, name, path, **metadata):
        """Create an UgorFile with the content read from path.

        Raises FileNotFoundError if the file is not found.
        """
        import mimetypes

        mime_type, encoding = mimetypes.guess_type(path)
        if mime_type:
            metadata.setdefault('mime_type', mime_type)
        if encoding:
            metadata.setdefault('encoding', encoding)

        content = open(path, 'rb').read()
        return cls.of(name, content, **metadata)

    def headers(self):
        """Return a dict with the metadata headers, as well as Content-Type
        and Content-Encoding. The headers are only included if they are set.

        The etag and modified headers must be set separately.
        """
        items = (
            ('Content-Type', self.mime_type),
            ('Content-Encoding', self.encoding),
            ('File-Description', self.description),
            ('File-Tag', self.tag),
            ('File-Tag2', self.tag2),
            ('File-Tag3', self.tag3),
            ('File-Data', self.data),
            ('File-Data2', self.data2),
            ('File-Data3', self.data3),
            ('File-Data4', self.data4),
            ('File-Data5', self.data5),
        )
        return {k: v for k, v in items if v}


# ------------------------------------------------------------------------------
# Utility functions

def auth(user=None, pwd=None):
    """Manage the Ugor authentication credentials.

    It always returns a tuple: (user, pwd).
    If user and/or pwd are given, it sets the credentials.
    If user/pwd are None and doesn't exist in the cache, it will prompt the user.
    """
    import cache

    if user:
        cache.primary['ugor_user'] = user
    if pwd:
        cache.primary['ugor_pwd'] = pwd

    if 'ugor_user' not in cache.primary:
        cache.primary['ugor_user'] = click.prompt('Ugor user', type=str)
    if 'ugor_pwd' not in cache.primary:
        cache.primary['ugor_pwd'] = click.prompt('Ugor pwd', type=str, hide_input=True)

    return cache.primary['ugor_user'], cache.primary['ugor_pwd']


def _url(name):
    """Get the URL for the given file name"""
    from urllib.parse import urljoin
    from config import ugor_url
    return urljoin(ugor_url, name)
