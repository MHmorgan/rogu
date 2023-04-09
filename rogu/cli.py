"""cli implements the command line interface for the rogu app."""
import sys
from functools import partial

# NOTE Only import the bare minimum here, to keep the startup time low.
import click
import log
from click import echo, style
from resources import Resource


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
@click.argument('uri')
@click.argument('path')
@click.option('-f', '--force', is_flag=True, help='Overwrite existing files.')
@click.option('--type', type=click.Choice(Resource.subclasses.keys()), help='Force resource type.')
@click.option('--etag', help='ETag precondition.')
@click.option('--modified', help='Modified precondition.')
def get(path, uri, force, **kwargs):
    """Get a resource from URI and write to PATH.

    URI may be a relative path or file name (an Ugor name), or a URL.
    """
    import rdsl

    resource = rdsl.fetch(path=path, uri=uri, **kwargs)

    # Only ignore uncategorized resources. Otherwise, we would ignore
    # resources which have previously been installed/updated.
    if not resource.category:
        resource.category |= Resource.IGNORE

    ok, msg = rdsl.install(resource, force=force)
    if msg:
        log.info(msg)
    if ok:
        rdsl.store(resource)


@cli.command()
@click.argument('uri')
@click.argument('path')
@click.option('-f', '--force', is_flag=True, help='Overwrite existing files.')
def install(path, uri, force):
    """Install a resource. The resource is fetched from URI and written to PATH.

    URI may be a relative path (an Ugor name), or a URL.

    Installed resources are kept up-to-date with update.
    """
    import rdsl

    resource = rdsl.fetch(path=path, uri=uri)
    ok, msg = rdsl.install(resource, force=force)
    if msg:
        log.info(msg)
    if ok:
        rdsl.store(resource)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.argument('uri')
@click.option('-f', '--force', is_flag=True, help='Overwrite existing files.')
def upload(path, uri, force):
    """Upload a resource from PATH to Ugor.

    URI must be a relative path or file name (an Ugor name).

    Uploaded resources are kept up-to-date with update.
    """
    import rdsl

    resource = rdsl.fetch(path=path, uri=uri)
    ok, msg = rdsl.upload(resource, force=force)
    if msg:
        log.info(msg)
    if ok:
        rdsl.store(resource)


@cli.command()
@click.argument('path')
@click.argument('uri')
def sync(path, uri):
    """Synchronise a resource. This is like a combination of
    update and install.

    URI must be a relative path or file name (an Ugor name).

    Synchronised resources are kept up-to-date with update.
    """
    import rdsl

    resource = rdsl.fetch(path=path, uri=uri)
    ok, msg = rdsl.sync(resource)
    if msg:
        log.info(msg)
    if ok:
        rdsl.store(resource)


@cli.command()
@click.option('-r', '--resource', 'key', help='Key of a resource to update.')
@click.option('-p', '--path', help='Path of a resource to update.')
@click.option('-u', '--uri', help='Name of a resource to update.')
@click.option('-f', '--force', is_flag=True, help='Overwrite existing files.')
def update(key, path, uri, force):  # TODO
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
        rs = cache.resources.values()

    kwargs = {}
    if force:
        kwargs['force'] = True

    for resource in rs:
        try:
            ok, msg = rdsl.update(resource, **kwargs)
        except AppError as e:
            log.error(e)
        else:
            log.info(msg)
            if ok:
                cache.resources[resource] = resource


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
    """
    import cache
    import resources
    import rdsl

    try:
        key = resources.expand_key(key)
    except ValueError:
        bail('Resource not found')

    ok, msg = rdsl.delete(
        cache.resources[key],
        local=local,
        remote=not no_remote,
        force=force,
    )
    log.info(msg)


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

    r = cache.resources[key]
    ok, msg = rdsl.move(r, path)
    log.info(msg)

    del cache.resources[key]
    cache.resources[r] = r


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

    echo_row(headers, widths)
    for entry in entries:
        color = green if entry.ok else red
        cols = [
            entry.timestamp.format(fmt),
            entry.action,
            entry.name,
            entry.path,
            color(entry.message),
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
        echo_ugor_file(file)
    except errors.UgorError404:
        bail('File not found')


@ugor.command('put')
@click.argument('file', type=click.Path(
    exists=True,
    dir_okay=False,
    readable=True,
))
@click.option('--name', help='Name of the file on the Ugor server.')
@click.option('-f', '--force', is_flag=True, help='Ignore failing preconditions.')
@click.option('--etag', help='ETag precondition.')
@click.option('--modified', help='Modified precondition.')
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

    try:
        file, created = ugor.put(file, name, **metadata)
    except errors.UgorError412:
        bail('Precondition failed')
    else:
        echo('Created file.' if created else 'Updated file.')
        echo_ugor_file(file, include=['name', 'etag', 'modified'])


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
    import cache
    import config
    import history
    import os

    w = 25

    echo(f'{bold("Version"):>{w}} {config.version}')
    echo(f'{bold("Python"):>{w}} {sys.version}')

    # Files
    echo()
    files = [
        ('App directory', config.app_dir),
        ('Primary cache', cache.primary_file),
        ('Resources cache', cache.resources_file),
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


# ------------------------------------------------------------------------------
# UTILS

bold = partial(style, bold=True)
red = partial(style, fg='red')
green = partial(style, fg='green')


def bail(*args, **kwargs):
    """Print a message and exit."""
    log.error(*args, **kwargs)
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
        'etag',
        'modified',
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
    to show the error message with log.error()
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

    log.error(self.format_message())


click.exceptions.UsageError.show = show_usage_error
