import sys
from functools import partial
from typing import Iterable

import click
from click import echo, style
from errors import *
from ui import *


@click.group()
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output.')
def cli(verbose):
    """\b
     ____
    |  _ \ ___   __ _ _   _
    | |_) / _ \ / _' | | | |
    |  _ < (_) | (_| | |_| |
    |_| \_\___/ \__, |\__,_|
                |___/

    Run 'rogu help' for more detailed help.
    """
    if verbose:
        import ui
        ui.VERBOSE = True


@cli.command()
@click.argument('name')
def get(name):
    """Get an Ugor file and print the content to stdout."""
    import ugor
    file = ugor.get(name)
    sys.stdout.buffer.write(file.content)


@cli.command()
@click.argument('name')
@click.option('-d', '--description', help='Description of the file.')
def put(name, description):
    """Put an Ugor file from stdin."""
    import ugor
    content = sys.stdin.buffer.read()
    ugor.put(obj=content, name=name, tag2='Rogu', description=description)


@cli.command('list')
@click.argument('name', required=False)
@click.option('-a', 'all_', is_flag=True, help='List all files, not only files owned by Rogu.')
@click.option('-s', 'size', is_flag=True, help='Show file size.')
def list_(name, all_, size):
    """List Ugor files. Optionally filter by NAME."""
    import ugor
    import utils

    params = {}
    if not all_:
        params['tag2'] = 'Rogu'
    if name:
        params['name'] = name

    try:
        names = ugor.find(**params)
    except UgorError440:
        bad('No files found.')
        return

    w = max(len(n) for n in names)
    widths = (w, 6) if size else (w,)
    for name in ugor.find(**params):
        header: ugor.FileHeader = ugor.get_header(name)
        desc = dim(header.description) if header.description else ''
        sz = utils.human_size(header.content_length)
        vals = (name, sz, desc) if size else (name, desc)
        echo_row(vals, widths)


# ------------------------------------------------------------------------------
# RESOURCE COMMANDS

@cli.command()
@click.argument('path')
@click.argument('uri')
@click.option('-m', 'mode', help='File mode.')
@click.option('-D', 'ignore_divergence', is_flag=True, help='Override divergence checks.')
@click.option('-C', 'ignore_conditionals', is_flag=True, help='Do not use conditional requests.')
def install(path, uri, mode, **kwargs):
    """Install a resource. The resource is fetched from URI and written to PATH.

    URI may be a relative path (an Ugor name), or a URL.

    Installed resources are kept up-to-date with update.
    """
    import rdsl

    if mode:
        mode = int(mode, 8)

    try:
        resource = rdsl.fetch(path=path, uri=uri)
        rdsl.install(resource, **kwargs)
    except ActionBlocked as e:
        warn(e)
    else:
        rdsl.store(resource)
        if mode:
            resource.path.chmod(mode)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.argument('uri')
@click.option('-D', 'ignore_divergence', is_flag=True, help='Override divergence checks.')
@click.option('-C', 'ignore_conditionals', is_flag=True, help='Do not use conditional requests.')
@click.option('-d', '--description', help='Description of the file.')
def upload(path, uri, description, **kwargs):
    """Upload a resource.

    To upload to Ugor, URI must be a relative path (an Ugor name).

    Uploaded resources are kept up-to-date with update.
    """
    import rdsl

    try:
        resource = rdsl.fetch(path=path, uri=uri, description=description)
        rdsl.upload(resource, **kwargs)
    except ActionBlocked as e:
        warn(e)
    else:
        rdsl.store(resource)


@cli.command()
@click.argument('path')
@click.argument('uri')
@click.option('-m', 'mode', help='File mode.')
@click.option('-D', 'ignore_divergence', is_flag=True, help='Override divergence checks.')
@click.option('-C', 'ignore_conditionals', is_flag=True, help='Do not use conditional requests.')
@click.option('-d', 'description', help='Description of the file.')
def sync(path, uri, mode, description, **kwargs):
    """Synchronise a resource. This is like a combination of
    update and install.

    URI must be a relative path or file name (an Ugor name).

    Synchronised resources are kept up-to-date with update.
    """
    import rdsl

    if mode:
        mode = int(mode, 8)

    try:
        resource = rdsl.fetch(path=path, uri=uri, description=description)
        rdsl.sync(resource, **kwargs)
    except ActionBlocked as e:
        warn(e)
    else:
        rdsl.store(resource)
        if mode:
            resource.path.chmod(mode)


@cli.command()
@click.option('-r', 'key', help='Key of a resource to update.')
@click.option('-p', 'path', help='Path of a resource to update.')
@click.option('-u', 'uri', help='Name of a resource to update.')
@click.option('-D', 'ignore_divergence', is_flag=True, help='Override divergence checks.')
@click.option('-C', 'ignore_conditionals', is_flag=True, help='Do not use conditional requests.')
def update(key, path, uri, **kwargs):
    """Update resources.

    If no resource is specified, all resources are updated.
    """
    import cache
    import rdsl
    import resources
    from errors import AppError

    if key:
        try:
            key = resources.expand_key(key)
        except ValueError:
            bail('Resource not found')
        rs = [cache.resources[key]]
    elif path or uri:
        if not (path and uri):
            bail('Both path and uri must be specified')
        rs = [resources.get(path, uri)]
    else:
        rs = list(cache.resources.values())

    # Prioritise uploaded resources, then all other resources.
    priority = [
        rdsl.is_uploaded,
        lambda _: True,
    ]

    code = 0
    for prioritized in priority:
        i = 0
        while i < len(rs):
            if not prioritized(rs[i]):
                i += 1
                continue

            try:
                resource = rs.pop(i)
                rdsl.update(resource, **kwargs)
            except ActionBlocked as e:
                warn(e)
            except AppError as e:
                err(e)
                code = 1
            else:
                rdsl.store(resource)

    sys.exit(code)


@cli.command()
@click.argument('key')
def rm(key):
    """Remove a resource.

    KEY is the key of the resource to remove.
    """
    import cache
    import resources
    import rdsl

    try:
        key = resources.expand_key(key)
    except ValueError:
        bail('Resource not found')

    try:
        rdsl.delete(cache.resources[key])
    except ActionBlocked as e:
        warn(e)


@cli.command()
@click.argument('key')
@click.argument('path')
def mv(key, path):
    """Move a resource locally.

    KEY is the resource key and PATH in the new local path.
    """
    import cache
    import resources
    import rdsl

    try:
        key = resources.expand_key(key)
    except ValueError:
        bail('Resource not found')

    try:
        r = cache.resources[key]
        rdsl.move(r, path)
    except ActionBlocked as e:
        warn(e)


@cli.command()
@click.argument('key', required=False)
def resources(key):
    """List resources.

    KEY may be used to filter the list.
    """
    import cache

    resources = [
        entries
        for entries in cache.resources.values()
        if not key or key in entries.key
    ]
    headers = ['KEY', 'TYPE', 'PATH', 'CATEGORY', 'URI']

    if not resources:
        echo('No resources to show')
        return

    widths = [
        max(len(r.short_key) for r in resources),
        max(len(r.class_name) for r in resources),
        max(len(r.short_path) for r in resources),
        8,  # Length of 'CATEGORY'
    ]

    echo_row(headers, widths)
    for r in sorted(resources, key=lambda r: r.short_path):
        cols = [
            r.short_key,
            r.class_name,
            r.short_path,
            f'0b{r.category:04b}',
            r.uri,
        ]
        echo_row(cols, widths)


@cli.command()
@click.argument('key')
def show(key):
    """Show information about a resource."""
    import cache
    import resources

    try:
        key = resources.expand_key(key)
    except ValueError:
        bail('Resource not found!')
    r = cache.resources[key]

    echo(f'Key: {r.key}')
    echo(f'Type: {r.class_name}')
    echo(f'Path: {r.path}')
    echo(f'Category: 0b{r.category:04b}')
    echo(f'URI: {r.uri}')
    echo(f'Current hash: {r.path_hash}')
    echo(f'Cached hash: {r.cached_hash}')


# ------------------------------------------------------------------------------
# UGOR

@cli.group()
def ugor():
    """Ugor commands."""
    pass


@ugor.command('info')
def ugor_info():
    """Get information about the Ugor server."""
    import ugor
    from pprint import pformat
    echo(pformat(ugor.info()))


@ugor.command('auth')
@click.option('--user', prompt=True, help='Ugor username.')
@click.password_option(help='Ugor password.')
def ugor_auth(user, password):
    """Set the Ugor username and password."""
    import ugor
    ugor.auth(user, password)


@ugor.command('get')
@click.argument('name')
def ugor_get(name):
    """Get file NAME from the Ugor server.

    This is mostly a debugging command which prints the file with metadata.
    Should not be used for downloading or installing files.
    """
    import ugor
    from requests import HTTPError

    try:
        file = ugor.get(name)
    except HTTPError as e:
        if e.response.status_code == 404:
            bail('File not found')
        raise AppError(f'getting file: {e}')
    else:
        echo_ugor_file(file)


@ugor.command('put')
@click.argument('file', type=click.Path(
    exists=True,
    dir_okay=False,
    readable=True,
))
@click.argument('name')
@click.option('-f', '--force', is_flag=True, help='Ignore failing preconditions.')
@click.option('--etag', 'last_etag', help='ETag precondition.')
@click.option('--modified', 'last_modified', help='Modified precondition.')
@click.option('--mime-type', help='MIME type of the file.')
@click.option('--encoding', help='Encoding of the file.')
@click.option('--description', help='Description of the file.')
@click.option('--tag', help='Tag of the file.')
@click.option('--tag2', help='Tag2 of the file.')
@click.option('--tag3', help='Tag3 of the file.')
@click.option('--data', help='Data of the file.')
@click.option('--data2', help='Data2 of the file.')
@click.option('--data3', help='Data3 of the file.')
@click.option('--data4', help='Data4 of the file.')
@click.option('--data5', help='Data5 of the file.')
def ugor_put(file, name, **metadata):
    """Upload FILE to the Ugor server as NAME.

    This is mostly a debugging command which uploads the file with metadata.
    Should not be used for normal uploading.
    """
    import ugor
    from pathlib import Path
    from requests import HTTPError

    try:
        ugor.put(Path(file), name, **metadata)
    except HTTPError as e:
        if e.response.status_code == 412:
            bail('Precondition failed')
        raise AppError(f'uploading file: {e}')


@ugor.command('rm')
@click.argument('name')
@click.option('-f', '--force', is_flag=True, help='Ignore failing preconditions.')
@click.option('--etag', help='ETag precondition.')
@click.option('--modified', help='Modified precondition.')
def ugor_rm(name, force, etag, modified):
    """Delete file NAME from the Ugor server."""
    import ugor
    from requests import HTTPError

    try:
        ugor.delete(name, force, etag, modified)
    except HTTPError as e:
        if e.response.status_code == 412:
            bail('Precondition failed')
        raise AppError(f'deleting file: {e}')


@ugor.command('find')
@click.option('--name', help='Name glob pattern.')
@click.option('--name-re', help='Name regular expression.')
@click.option('--tag', help='Tag exact match.')
@click.option('--tag2', help='Tag2 exact match.')
@click.option('--tag3', help='Tag3 exact match.')
@click.option('--encoding', help='Encoding exact match.')
@click.option('--mime', help='MIME type glob pattern.')
@click.option('--modified', help='Modified exact time.')
@click.option('--mod-before', help='Modified before time.')
@click.option('--mod-after', help='Modified after time.')
@click.option('--size', help='Size exact match.')
@click.option('--size-gt', help='Size greater than.')
@click.option('--size-lt', help='Size less than.')
@click.option('--recursive', is_flag=True, default=True, help='Search recursively.')
def ugor_find(**params):
    """Find files on the Ugor server."""
    import ugor
    from requests import HTTPError
    from pprint import pformat
    try:
        echo(pformat(ugor.find(**params)))
    except HTTPError as e:
        if e.response.status_code == 440:
            bail('No matches')
        raise AppError(f'finding files: {e}')


@ugor.command('list')
def ugor_list():
    """List files on the Ugor server."""
    import ugor
    from requests import HTTPError

    try:
        names = ugor.find()
        for name in sorted(names):
            echo(name)
    except HTTPError as e:
        if e.response.status_code == 440:
            bail('No matches')
        raise AppError(f'finding files: {e}')


# ------------------------------------------------------------------------------
# CLI MISC

@cli.command()
def info():
    """Show Rogu information."""
    import cache
    import config
    import os
    import shutil
    import ugor

    def show(lbl, txt):
        if txt is None:
            txt = '<not found>'
        txt = str(txt).split('\n')[0]
        echo(f'{bold(lbl):>{24}} {txt}')

    def hr():
        echo('-----'.rjust(19))

    show('Version', config.version)
    show('Python', sys.version)
    show('Debug', __debug__)
    show('App Directory', config.app_dir)
    show('Ugor URL', config.ugor_url)
    show('Resources', len(cache.resources))

    hr()
    show('Rogu', shutil.which('rogu'))
    show('Python', sys.executable)
    show('Homebrew', shutil.which('brew'))
    show('Git', shutil.which('git'))
    show('GitHub CLI', shutil.which('gh'))

    # Ugor server info
    if uinfo := ugor.info():
        hr()
        for key, val in uinfo.items():
            show(f'Ugor {key}', val)

    # Environment
    first = True
    for name in sorted(config.env_vars.values()):
        if val := os.environ.get(name):
            if first:
                hr()
                first = False
            show(name, val)


@cli.command('help')
def help_():
    """Print detailed help."""
    echo(HELP)


@cli.command('key')
@click.argument('path')
@click.argument('uri')
@click.option('--exists', is_flag=True, help='Check if the resource exists.')
def resource_key(path, uri, exists):
    """Print the resource key for PATH and URI."""
    import cache
    import resources

    key = resources.cache_key(path, uri)
    if exists and key not in cache.resources:
        bail('Resource not found')
    echo(key, nl=False)


# ------------------------------------------------------------------------------
# UTILS

dim = partial(style, dim=True)
bold = partial(style, bold=True)
red = partial(style, fg='red')
green = partial(style, fg='green')


def bail(*args, **kwargs):
    """Print a message and exit."""
    err(*args, **kwargs)
    sys.exit(1)


def echo_ugor_file(file, exclude=None, include=None):
    """Dump the UgorFile to stdout.

    If an include list is given only those attributes will be dumped.
    Any attributes in the exclude list will be skipped.
    Attributes with None values will be skipped as well.
    """
    from functools import partial

    label = partial(style, bold=True)

    attributes = include if include else [
        'name',
        'content',
        'mime_type',
        'encoding',
        'last_etag',
        'last_modified',
        'description',
        'tag',
        'tag2',
        'tag3',
        'data',
        'data2',
        'data3',
        'data4',
        'data5',
    ]
    width = max(map(len, attributes))

    for attr in attributes:
        if exclude and attr in exclude or attr == 'content':
            continue
        if (val := getattr(file, attr, None)) is not None:
            lbl = attr.replace('_', ' ').title().ljust(width)
            echo(f"{label(lbl)} {val}")

    if not (exclude and 'content' in exclude) and 'content' in attributes:
        echo(f'\n{label("Content")}\n{file.content}')


def echo_row(cols: Iterable[str], widths: Iterable[int], sep: str = '  '):
    """Echo a row of items with the given widths."""
    from itertools import zip_longest

    echo(sep.join(
        item.ljust(width)
        for item, width in zip_longest(cols, widths, fillvalue=0)
    ))


def show_usage_error(self, *args) -> None:
    """Modified version of click.exceptions.UsageError.show()
    to show the error message with error()
    """

    hint = ""
    if (
            self.ctx is not None
            and self.ctx.command.get_help_option(self.ctx) is not None
    ):
        hint = "Try '{command} {option}' for help.".format(
            command=self.ctx.command_path, option=self.ctx.help_option_names[0]
        )
        hint = f"{hint}\n"

    if self.ctx is not None:
        echo(f"{self.ctx.get_usage()}\n{hint}", color=self.ctx.color, err=True)

    err(self.format_message())


click.exceptions.UsageError.show = show_usage_error

# ------------------------------------------------------------------------------
# TEXT

HELP = """
Ugor
====

Rogu is a Ugor client with extended functionality.
All files uploaded/put to Ugor by Rogu is tagged with `tag2=Rogu`, and any
resource uploaded use `data2` to store the local hash of the resource.

Additionally, Rogu himself may be installed from Ugor by a GET request
without a path.


CLI Basics
==========

The CLI provides some basic commands which do not deal with resources.
These are `get`, `put` and `list`, and are used for basic interaction with
Ugor.

The `ugor` command group provides commands for interacting with Ugor. However,
these are intended for debugging and testing purposes only.


Resources
=========

Everything revolves around resources. A resource is uniquely identified by a
path and a URI. The path is a local file or directory. The URI contains
information about the remote location of the resource. Each resource has its
own custom URI format.

## Files

Files can be installed/uploaded/synced with Ugor. The file URIs look like this:

    ugor://file/<name>

## Archives

Archives can be installed/uploaded/synced with Ugor. They are directories locally
stored in an archive format in Ugor. The archive URIs look like this:

    ugor://archive/<name>?format=<format>

Where the format is one of 'zip', 'tar', 'gztar', 'bztar', 'xztar'.
It defaults to 'xztar'.

## Releases

GitHub releases can be installed with Rogu. The release URIs look like this:

    release://<repo>@<user>/<file>
    
This kind of resource only supports the 'install' command.
"""
