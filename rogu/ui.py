"""
log provides the logging functionality for Rogu.

log has no import side effects, and can be imported globally.

Since Rogu is a command line application, all logging is
printed to stderr. This allows the user to redirect the
output to a file or pipe it to another program.
"""

from click import echo, secho


__all__ = ['err', 'warn', 'good', 'bad', 'debug']


VERBOSE = False


def err(*args, sep=' ', **kwargs):
    s = sep.join(str(m) for m in args)
    kwargs.setdefault('fg', 'red')
    kwargs.setdefault('bold', True)
    kwargs.setdefault('err', True)
    secho(f'Error: {s}', **kwargs)


def warn(*args, sep=' ', **kwargs):
    s = sep.join(str(m) for m in args)
    kwargs.setdefault('fg', 'yellow')
    kwargs.setdefault('bold', True)
    kwargs.setdefault('err', True)
    secho(f'Warn: {s}', **kwargs)


def debug(*args, sep=' ', **kwargs):
    if __debug__:
        s = sep.join(str(m) for m in args)
        kwargs.setdefault('dim', True)
        kwargs.setdefault('err', True)
        secho('[*] ' + s, **kwargs)


def verbose(*args, sep=' ', **kwargs):
    if VERBOSE:
        s = sep.join(str(m) for m in args)
        echo('[*] ' + s, **kwargs)


def good(*args, sep=' ', **kwargs):
    s = sep.join(str(m) for m in args)
    kwargs.setdefault('fg', 'green')
    kwargs.setdefault('bold', True)
    secho(s, **kwargs)


def bad(*args, sep=' ', **kwargs):
    s = sep.join(str(m) for m in args)
    kwargs.setdefault('fg', 'red')
    kwargs.setdefault('bold', True)
    secho(s, **kwargs)

