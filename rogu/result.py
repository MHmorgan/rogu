"""result implements Result type returned by RDSL resource actions."""

from functools import partial

__all__ = ['Result', 'Ok', 'Fail']


class Result:
    """Result is the return type used for resource actions.

    :param success: True if the resource action succeeded.
    :param messages: the messages to add.
    """

    def __init__(self, success, *messages):
        self.success = success
        self.messages = list(messages)

    def __call__(self, msg, other=None):
        """Add a message to the result and join another result.

        :param msg: the message to add.
        :param other: optional: another ``Result`` object to join.
        :return: *self*
        """
        if other:
            self.join(other)
        self.messages.append(str(msg))

        return self

    def __eq__(self, other):
        return (self.success == other.success and
                self.messages == other.messages)

    def __bool__(self):
        return self.success

    @property
    def is_success(self):
        return self.success

    @property
    def is_failure(self):
        return not self.success

    # ------------------------------------------------------
    # DISPLAY

    def __str__(self):
        return self.message

    def __repr__(self):
        return f'<Result {self.success} {self.message!r}>'

    def __format__(self, fmt):
        # Max message width.
        try:
            n = int(fmt)
        except ValueError:
            pass
        else:
            from textwrap import shorten
            return shorten(self.message, n, break_long_words=True)

        # Magic format strings.
        try:
            if fmt == 'last':
                return self.messages[-1]
            elif fmt == 'first':
                return self.messages[0]
            elif fmt == 'successful':
                return 'successful' if self.success else 'unsuccessful'
            elif fmt == 'success':
                return 'success' if self.success else 'failure'
        except IndexError:
            return ''

        # Otherwise, use fmt as prefix to each message line.
        return f'\n{fmt}'.join(self.messages)

    @property
    def message(self):
        # Put the latest messages first.
        txt = '; '.join(reversed(self.messages))
        return txt + '.' if txt else ''

    # ------------------------------------------------------
    # COMBINING RESULTS

    def __add__(self, obj):
        """Add a message or another result to the result.

        :param obj: ``str`` or ``Result`` to combine.
        :return: *self*
        """
        if isinstance(obj, Result):
            return self.join(obj)
        else:
            self.messages.append(str(obj))
        return self

    __iadd__ = __add__
    __radd__ = __add__

    def join(self, other):
        """Join another result to this result.

        This sets ``self.success = other.success`` and combines the messages.

        :param other: another ``Result`` object.
        :return: a new ``Result`` object.
        """
        assert isinstance(other, Result)
        self.messages.extend(other.messages)
        self.success = other.success
        return self


Ok = partial(Result, True)
Fail = partial(Result, False)
