"""
cli implements the command line interface for the rogu app.
"""
import sys

# NOTE Only import the bare minimum here, to keep the startup time low.
import click
import log
from click import echo, style


@click.group()
def cli():
    pass


@cli.command()
def version():
    """Print the rogu version."""
    import config
    echo(config.version)


# ------------------------------------------------------------------------------
# Ugor

@cli.group()
def ugor():
    """Ugor commands."""
    pass


@ugor.command()
def info():
    """Get information about the Ugor server."""
    import ugor
    from pprint import pformat
    echo(pformat(ugor.info()))


@ugor.command()
def find():
    """Find files on the Ugor server."""
    import ugor
    import errors
    from pprint import pformat
    try:
        echo(pformat(ugor.find()))
    except errors.UgorError440:
        log.bad('No matches')
        sys.exit(1)


@ugor.command()
@click.option('--user', prompt=True, help='Ugor username.')
@click.password_option(help='Ugor password.')
def auth(user, password):
    """Set the Ugor username and password."""
    import ugor
    ugor.auth(user, password)


@ugor.command()
@click.argument('name')
def get(name):
    """Get file NAME from the Ugor server.

    This is mostly a debugging command which prints the file with metadata.
    Should not be used for downloading or installing files.
    """
    import ugor
    import errors

    try:
        file = ugor.get(name)
        dump_ugor_file(file)
    except errors.UgorError404:
        log.bad('File not found')
        sys.exit(1)


@ugor.command()
@click.argument('file', type=click.Path(
    exists=True,
    dir_okay=False,
    readable=True,
))
@click.option('--name', help='Name of the file on the Ugor server.')
@click.option('--force', is_flag=True, help='Ignore failing preconditions.')
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
def put(file, name, **metadata):
    """Upload FILE to the Ugor server as NAME.

    This is mostly a debugging command which uploads the file with metadata.
    Should not be used for normal uploading.
    """
    import ugor
    import errors

    try:
        file = ugor.put(file, name, **metadata)
    except errors.UgorError412:
        log.bad('Precondition failed')
        sys.exit(1)
    dump_ugor_file(file, include=['name', 'etag', 'modified'])


@ugor.command()
@click.argument('name')
@click.option('--force', is_flag=True, help='Ignore failing preconditions.')
@click.option('--etag', help='ETag precondition.')
@click.option('--modified', help='Modified precondition.')
def delete(name, force, etag, modified):
    """Delete file NAME from the Ugor server."""
    import ugor
    import errors

    try:
        ugor.delete(name, force, etag, modified)
    except errors.UgorError412:
        log.bad('Precondition failed')
        sys.exit(1)


# ------------------------------------------------------------------------------
# Utils

def show(self, *args) -> None:
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


click.exceptions.UsageError.show = show


def dump_ugor_file(file, exclude=None, include=None):
    """Dump the UgorFile to stdout.

    If an include list is given only those attributes will be dumped.
    Any attributes in the exclude list will be skipped.
    Attributes with None values will be skipped as well.
    """
    from functools import partial

    label = partial(style, bold=True)

    attributes = include if include else [
        'name',
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
        if exclude and attr in exclude:
            continue
        if (val := getattr(file, attr, None)) is not None:
            lbl = attr.replace('_', ' ').title().ljust(width)
            echo(f"{label(lbl)} {val}")

    if not (exclude and 'content' in exclude) and 'content' in attributes:
        echo(f'\n{label("Content")}\n{file.content}')
