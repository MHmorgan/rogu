"""Handles the communication with the Ugor server"""

from collections import namedtuple
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Optional, Any, Union, List, Dict, Tuple

import click
import requests
from errors import AppError, UgorError
from ui import *

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
def get(
        name: str,
        etag: str = None,
        modified: str = None
) -> Optional['UgorFile']:
    """Get a file from the Ugor server.

    Use etag and modified to check if the file is updated.
    Modified may be a string or an object with a isoformat() method
    (like datetime.datetime and arrow.Arrow).

    :raises UgorError404: if the file doesn't exist.
    :return: a UgorFile object or None if the file is not modified.
    """
    headers = {}
    if etag:
        headers['If-None-Match'] = etag
    if modified:
        if hasattr(modified, 'isoformat'):
            modified = modified.isoformat()
        headers['If-Modified-Since'] = modified

    url = _url(name)
    debug(f'GET {url!r}', *[f"{k}: {v!r}" for k, v in headers.items()])

    r = requests.get(url, auth=auth(), headers=headers)
    r.raise_for_status()
    if r.status_code == 304:
        return None
    return UgorFile.of_response(name, r)


FileHeader = namedtuple('FileHeader', [
    'name',
    'content_type',
    'content_length',
    'modified',
    'etag',
    'description',
    'tag',
    'tag2',
    'tag3',
    'data',
    'data2',
    'data3',
    'data4',
    'data5',
])


@_ugor_error
def get_header(name: str) -> FileHeader:
    """Get the header of a file on the Ugor server.

    :returns: a FileHeader object.
    """
    url = _url(name)
    debug('HEAD', url)
    r = requests.head(url, auth=auth())
    r.raise_for_status()
    return FileHeader(
        name=name,
        content_type=r.headers['Content-Type'],
        content_length=int(r.headers['Content-Length']),
        modified=r.headers['Last-Modified'],
        etag=r.headers['ETag'],
        description=r.headers.get('File-Description'),
        tag=r.headers.get('File-Tag'),
        tag2=r.headers.get('File-Tag2'),
        tag3=r.headers.get('File-Tag3'),
        data=r.headers.get('File-Data'),
        data2=r.headers.get('File-Data2'),
        data3=r.headers.get('File-Data3'),
        data4=r.headers.get('File-Data4'),
        data5=r.headers.get('File-Data5'),
    )


@_ugor_error
def put(
        obj: Union[Path, str, bytes],
        name: str,
        force: bool = False,
        **metadata
) -> 'UgorFile':
    """Upload something to the Ugor server.

    If obj is a Path it will be uploaded as a file.

    if obj is string/bytes it will be uploaded as the file content.

    If force is True, the file will be uploaded even if the ETag or
    Last-Modified preconditions fails.

    The metadata will be passed along to the UgorFile constructor.

    :param obj: Path, str or bytes.
    :param name: the Ugor file name.
    :param force: force upload even if preconditions fail.
    :raises UgorError412: if any of the preconditions fails.
    :raises FileNotFoundError: if obj is a file path that doesn't exist.
    :return: the uploaded UgorFile with new ETag and Last-Modified values.
    """
    from pathlib import Path

    # Create Ugor file object
    if isinstance(obj, Path):
        debug(f'Ugor put file: from path {obj!r}')
        file = UgorFile.of_file(name or obj.name, obj, **metadata)
    elif isinstance(obj, (str, bytes)):
        debug(f'Ugor put file: with str/bytes content, named {name!r}')
        file = UgorFile.of(name, obj, **metadata)
    else:
        raise TypeError(f'obj must be a Path, str or bytes, not {type(obj)}')

    headers = file.headers()
    if file.last_etag and not force:
        headers['If-Match'] = file.last_etag
    if file.last_modified and not force:
        headers['If-Unmodified-Since'] = file.last_modified

    url = _url(file.name)
    debug('PUT', url, *[f"{k}: {v!r}" for k, v in headers.items()])
    r = requests.put(url, auth=auth(), headers=headers, data=file.content)
    r.raise_for_status()

    try:
        file.last_etag = r.headers['ETag']
        file.last_modified = r.headers['Last-Modified']
    except KeyError as e:
        raise AppError(f'Ugor server did not return ETag and/or Last-Modified headers') from e

    if r.status_code == 201:
        debug('Ugor put: Created', file.name)
    elif r.status_code == 200:
        debug('Ugor put: Updated', file.name)
    return file


@_ugor_error
def delete(
        name: str,
        force: bool = False,
        etag: str = None,
        modified: str = None
):
    """Delete a file from the Ugor server"""
    headers = {}
    if etag and not force:
        headers['If-Match'] = etag
    if modified and not force:
        if hasattr(modified, 'isoformat'):
            modified = modified.isoformat()
        headers['If-Unmodified-Since'] = modified

    url = _url(name)
    debug('DELETE', url, *[f"{k}: {v!r}" for k, v in headers.items()])
    r = requests.delete(url, auth=auth(), headers=headers)
    r.raise_for_status()


@_ugor_error
def find(**params) -> List[str]:
    """Find files on the Ugor server with the given search parameters"""
    from config import ugor_url

    params = {k: v for k, v in params.items() if v is not None}
    debug('FIND', ugor_url, params)
    r = requests.request('FIND', ugor_url, auth=auth(), json=params)
    r.raise_for_status()
    return r.json()


@_ugor_error
def info() -> Dict[str, Any]:
    """Get information about the Ugor server"""
    from config import ugor_url

    debug('INFO', ugor_url)
    r = requests.request('INFO', ugor_url, auth=auth())
    r.raise_for_status()
    return r.json()


@_ugor_error
def exists(name: str) -> bool:
    """Check if a file exists on the Ugor server"""
    url = _url(name)
    debug('HEAD', url)
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

        assert self.name and isinstance(self.name, str), \
            'name must be given and be a string'
        assert self.content and isinstance(self.content, bytes), \
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
    def of(cls, name: str, content: Union[str, bytes], **metadata) -> 'UgorFile':
        """Create an UgorFile from a name and content."""
        if isinstance(content, str):
            content = content.encode()
        elif not isinstance(content, bytes):
            raise TypeError('content must be a string or bytes')
        return cls(name=name, content=content, **metadata)

    @classmethod
    def of_response(cls, name: str, response: requests.Response) -> 'UgorFile':
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
    def of_file(cls, name: str, path: Union[Path, str], **metadata) -> 'UgorFile':
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

    def headers(self) -> Dict[str, str]:
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

def auth(user: str = None, pwd: str = None) -> Tuple[str, str]:
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


def _url(name: str) -> str:
    """Get the URL for the given file name"""
    from urllib.parse import urljoin
    from config import ugor_url
    return urljoin(ugor_url, name)
