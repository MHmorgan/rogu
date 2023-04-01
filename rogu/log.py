"""
log provides the logging functionality for Rogu.

Since Rogu is a command line application, all logging is
printed to stderr. This allows the user to redirect the
output to a file or pipe it to another program.
"""
from functools import partial

from click import secho


__all__ = ['error', 'warn', 'good', 'bad', 'info', 'debug']


def error(*msg, sep=' ', pre='[!!] ', **kwargs):
    s = sep.join(str(m) for m in msg).replace('\n', ' ')
    kwargs.setdefault('fg', 'red')
    kwargs.setdefault('bold', True)
    kwargs.setdefault('err', True)
    secho(pre + s, **kwargs)


def warn(*msg, sep=' ', pre='[!] ', **kwargs):
    s = sep.join(str(m) for m in msg).replace('\n', ' ')
    kwargs.setdefault('fg', 'yellow')
    kwargs.setdefault('bold', True)
    kwargs.setdefault('err', True)
    secho(pre + s, **kwargs)


def good(*msg, sep=' ', pre='[+] ', **kwargs):
    s = sep.join(str(m) for m in msg).replace('\n', ' ')
    kwargs.setdefault('fg', 'green')
    kwargs.setdefault('bold', True)
    kwargs.setdefault('err', True)
    secho(pre + s, **kwargs)


bad = partial(error, pre='[-] ')


def info(*msg, sep=' ', pre='[*] ', **kwargs):
    s = sep.join(str(m) for m in msg).replace('\n', ' ')
    kwargs.setdefault('err', True)
    secho(pre + s, **kwargs)


def debug(*msg, sep=' ', pre='[ ] ', **kwargs):
    if __debug__:
        s = sep.join(str(m) for m in msg).replace('\n', ' ')
        kwargs.setdefault('dim', True)
        kwargs.setdefault('err', True)
        secho(pre + s, **kwargs)
