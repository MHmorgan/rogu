"""
log provides the logging functionality for Rogu.

log has no import side effects, and can be imported globally.

Since Rogu is a command line application, all logging is
printed to stderr. This allows the user to redirect the
output to a file or pipe it to another program.
"""
from functools import partial

from click import secho


__all__ = ['error', 'warn', 'good', 'bad', 'info', 'debug']


def error(*args, sep=' ', pre='[!!] ', **kwargs):
    s = sep.join(str(m) for m in args).replace('\n', ' ')
    kwargs.setdefault('fg', 'red')
    kwargs.setdefault('bold', True)
    kwargs.setdefault('err', True)
    secho(pre + s, **kwargs)


def warn(*args, sep=' ', pre='[!] ', **kwargs):
    s = sep.join(str(m) for m in args).replace('\n', ' ')
    kwargs.setdefault('fg', 'yellow')
    kwargs.setdefault('bold', True)
    kwargs.setdefault('err', True)
    secho(pre + s, **kwargs)


def good(*args, sep=' ', pre='[+] ', **kwargs):
    s = sep.join(str(m) for m in args).replace('\n', ' ')
    kwargs.setdefault('fg', 'green')
    kwargs.setdefault('bold', True)
    kwargs.setdefault('err', True)
    secho(pre + s, **kwargs)


bad = partial(error, pre='[-] ')


def info(*args, sep=' ', pre='[*] ', **kwargs):
    s = sep.join(str(m) for m in args).replace('\n', ' ')
    kwargs.setdefault('err', True)
    secho(pre + s, **kwargs)


def debug(*args, sep=' ', pre='[ ] ', **kwargs):
    if __debug__:
        s = sep.join(str(m) for m in args).replace('\n', ' ')
        kwargs.setdefault('dim', True)
        kwargs.setdefault('err', True)
        secho(pre + s, **kwargs)
