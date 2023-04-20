"""cli implements the command line interface for the rogu app."""
import sys
from functools import partial

# NOTE Only import the bare minimum here, to keep the startup time low.
import click
from click import echo, style
from ui import *


# TODO Support scripts in CLI
#
# Use a 'script' cli group to manage scripts?
# Run scripts with 'rogu run <script>' or 'rogu <script>'
# or 'rogu script run <script>'?

# TODO Improve CLI help text. Group the commands into categories?


@click.group()
def cli():
    pass


@cli.command()
@click.argument('name')
def get(name):
    """Get an Ugor file and print it to stdout."""
    import ugor
    file = ugor.get(name)
    sys.stdout.buffer.write(file.content)


@cli.command()
@click.argument('name')
def put(name):
    """Put an Ugor file from stdin."""
    import ugor
    content = sys.stdin.buffer.read()
    ugor.put(obj=content, name=name)


# ------------------------------------------------------------------------------
# RESOURCE COMMANDS

@cli.command()
@click.argument('path')
@click.argument('uri')
@click.option('-m', '--mode', type=int, default=0o644, help='File mode.')
@click.option('-f', '--force', is_flag=True, help='Overwrite existing files.')
def install(path, uri, mode, force):
    """Install a resource. The resource is fetched from URI and written to PATH.

    URI may be a relative path (an Ugor name), or a URL.

    Installed resources are kept up-to-date with update.

    Returns 2 if the resource action is blocked, 1 for errors, and 0 for
    success.
    """
    import rdsl

    resource = rdsl.fetch(path=path, uri=uri, mode=mode)
    res = rdsl.install(resource, force=force)
    if res.is_success:
        rdsl.store(resource)

    txt = format(res, '    ')
    echo(txt.capitalize())
    sys.exit(0 if res else 2)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.argument('uri')
@click.option('-f', '--force', is_flag=True, help='Overwrite existing files.')
def upload(path, uri, force):
    """Upload a resource.

    To upload to Ugor, URI must be a relative path (an Ugor name).

    Uploaded resources are kept up-to-date with update.

    Returns 2 if the resource action is blocked, 1 for errors, and 0 for
    success.
    """
    import rdsl

    resource = rdsl.fetch(path=path, uri=uri)
    res = rdsl.upload(resource, force=force)
    if res.is_success:
        rdsl.store(resource)

    txt = format(res, '    ')
    echo(txt.capitalize())
    sys.exit(0 if res else 2)


@cli.command()
@click.argument('path')
@click.argument('uri')
@click.option('-m', '--mode', type=int, default=0o644, help='File mode.')
def sync(path, uri, mode):
    """Synchronise a resource. This is like a combination of
    update and install.

    URI must be a relative path or file name (an Ugor name).

    Synchronised resources are kept up-to-date with update.

    Returns 2 if the resource action is blocked, 1 for errors, and 0 for
    success.
    """
    import rdsl

    resource = rdsl.fetch(path=path, uri=uri, mode=mode)
    res = rdsl.sync(resource)
    if res.is_success:
        rdsl.store(resource)

    txt = format(res, '    ')
    echo(txt.capitalize())
    sys.exit(0 if res else 2)


@cli.command()
@click.option('-r', '--resource', 'key', help='Key of a resource to update.')
@click.option('-p', '--path', help='Path of a resource to update.')
@click.option('-u', '--uri', help='Name of a resource to update.')
def update(key, path, uri):
    """Update resources.

    If no resource is specified, all resources are updated.

    Returns 2 if the resource action is blocked, 1 for errors, and 0 for
    success.
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
                res = rdsl.update(resource)
            except AppError as e:
                err(e)
                code = 1
                continue

            txt = format(res, '    ')
            echo(txt.capitalize())
            if res:
                rdsl.store(resource)

    sys.exit(code)


@cli.command()
@click.argument('key')
@click.option('-l', '--local', is_flag=True, help='Delete the local copy of the resource.')
@click.option('-f', '--force', is_flag=True, help='Force removal of the resource.')
@click.option('-R', '--no-remote', is_flag=True, help='Do not remove Ugor file from server.')
def rm(key, local, force, no_remote):
    """Remove a resource.

    KEY is the key of the resource to remove.

    With --local, the local copy of the resource is removed if it exists.

    Without --no-remote and if the resource URI is an Ugor name, the Ugor file is
    removed from the server.

    Returns 2 if the resource action is blocked, 1 for errors, and 0 for
    success.
    """
    import cache
    import resources
    import rdsl

    try:
        key = resources.expand_key(key)
    except ValueError:
        bail('Resource not found')

    res = rdsl.delete(
        cache.resources[key],
        local=local,
        remote=not no_remote,
        force=force,
    )
    txt = format(res, '    ')
    echo(txt.capitalize())
    sys.exit(0 if res else 2)


@cli.command()
@click.argument('key')
@click.argument('path')
def mv(key, path):
    """Move a resource locally.

    KEY is the resource key and PATH in the new local path.

    Returns 2 if the resource action is blocked, 1 for errors, and 0 for
    success.
    """
    import cache
    import resources
    import rdsl

    try:
        key = resources.expand_key(key)
    except ValueError:
        bail('Resource not found')

    r = cache.resources[key]
    res = rdsl.move(r, path)
    del cache.resources[key]
    cache.resources[r] = r

    txt = format(res, '    ')
    echo(txt.capitalize())
    sys.exit(0 if res else 2)


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


# ------------------------------------------------------------------------------
# HISTORY

@cli.command()
@click.option('-n', type=int, default=20, help='Number of entries to show (-1 means everything).')
def history(n):
    """Show the resource action history."""
    import history
    import shutil
    import textwrap

    entries = [
        entry
        for i, entry in enumerate(history.entries())
        if i < n or n == -1
    ]
    fmt = 'YYYY-MM-DD HH:mm:ss'
    headers = ['TIME', 'ACTION', 'NAME', 'PATH', 'MESSAGE']

    if not entries:
        echo('No history to show')
        return

    widths = [
        max(len(e.timestamp.format(fmt)) for e in entries),
        max(len(e.action) for e in entries),
        max(len(e.name) for e in entries),
        max(len(e.path) for e in entries),
    ]

    # Calculate left-over width for message column.
    w, _ = shutil.get_terminal_size()
    msg_width = w - sum(widths) - 2 * len(widths)

    echo_row(headers, widths)
    for entry in entries:
        color = green if entry.ok else red
        msg = textwrap.shorten(
            entry.message,
            msg_width,
            break_long_words=True,
        )
        cols = [
            entry.timestamp.format(fmt),
            entry.action,
            entry.name,
            entry.path,
            color(msg),
        ]
        echo_row(cols, widths)


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
    import errors

    try:
        file = ugor.get(name)
    except errors.UgorError404:
        bail('File not found')
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
    import errors
    from pathlib import Path

    try:
        ugor.put(Path(file), name, **metadata)
    except errors.UgorError412:
        bail('Precondition failed')


@ugor.command('delete')
@click.argument('name')
@click.option('-f', '--force', is_flag=True, help='Ignore failing preconditions.')
@click.option('--etag', help='ETag precondition.')
@click.option('--modified', help='Modified precondition.')
def ugor_delete(name, force, etag, modified):
    """Delete file NAME from the Ugor server."""
    import ugor
    import errors

    try:
        ugor.delete(name, force, etag, modified)
    except errors.UgorError412:
        bail('Precondition failed')


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
    import errors
    from pprint import pformat
    try:
        echo(pformat(ugor.find(**params)))
    except errors.UgorError440:
        bail('No matches')


@ugor.command('list')
def ugor_list():
    """List files on the Ugor server."""
    import ugor
    import errors

    try:
        names = ugor.find()
        for name in sorted(names):
            echo(name)
    except errors.UgorError440:
        bail('No matches')


# ------------------------------------------------------------------------------
# CLI MISC

@cli.command()
def version():
    """Print the rogu version."""
    import config
    echo(config.version)


@cli.command()
def doctor():
    """Analyze the Rogu installation."""
    import config
    import history
    import os

    w = 24

    echo(f'{bold("Version"):>{w}} {config.version}')
    echo(f'{bold("Python"):>{w}} {sys.version}')

    # TODO Statistics

    # Files
    echo()
    files = [
        ('App directory', config.app_dir),
        ('History file', history.history_file),
    ]
    for label, path in files:
        echo(f'{bold(label):>{w}} {path}')

    # Config
    echo()
    for name in sorted(config.defaults):
        val = getattr(config, name)
        echo(f'{bold(name):>{w}} {val}')

    # Environment
    echo()
    for name in sorted(config.env_vars.values()):
        if val := os.environ.get(name):
            echo(f'{bold(name):>{w}}={val}')


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


def echo_row(cols, widths, sep='  '):
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
Files
=====

Files can be installed/uploaded/synced with Ugor. The file URIs look like this:

    ugor://file/<name>

Archives
========

Archives can be installed/uploaded/synced with Ugor. They are directories locally
stored in an archive format in Ugor. The archive URIs look like this:

    ugor://archive/<name>?format=<format>

Where the format is one of 'zip', 'tar', 'gztar', 'bztar', 'xztar'.
It defaults to 'xztar'.

Releases
========

GitHub releases can be installed with Rogu. The release URIs look like this:

    release://<repo>@<user>/<file>
    
This kind of resource only supports the 'install' command.

CLI
===

Resource action commands returns 2 if the action is blocked, 0 on success and
1 on error.
"""
