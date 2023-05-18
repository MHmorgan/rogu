from click import echo, secho


__all__ = ['err', 'warn', 'good', 'bad', 'debug', 'verbose']


VERBOSE = False


def err(*args, sep=' ', **kwargs):
    s = sep.join(str(m) for m in args)
    kwargs.setdefault('fg', 'red')
    kwargs.setdefault('bold', True)
    kwargs.setdefault('err', True)
    secho(f'ERROR: {s}', **kwargs)


def warn(*args, sep=' ', **kwargs):
    s = sep.join(str(m) for m in args)
    kwargs.setdefault('fg', 'yellow')
    kwargs.setdefault('bold', True)
    kwargs.setdefault('err', True)
    secho(f'WARN: {s}', **kwargs)


def debug(*args, sep=' ', **kwargs):
    if __debug__:
        s = sep.join(str(m) for m in args)
        kwargs.setdefault('dim', True)
        kwargs.setdefault('err', True)
        secho(s, **kwargs)


def verbose(*args, sep=' ', **kwargs):
    if VERBOSE or __debug__:
        s = sep.join(str(m) for m in args)
        kwargs.setdefault('err', True)
        echo(s, **kwargs)


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

