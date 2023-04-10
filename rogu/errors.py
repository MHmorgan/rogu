"""errors defines all custom exceptions used in this application.

errors has no import side effects, and can be imported globally.
"""


class AppError(Exception):
    """Base class for all application errors.

    These errors should represent errors that are understood
    by the user and doesn't require a stack trace.
    """
    pass


class ResourceNotFound(AppError):
    """Resource not found errors."""

    def __init__(self, uri, path):
        self.uri = uri
        self.path = path
        super().__init__(f'No resource found for uri={uri} and path={path}')


class ActionBlocked(AppError):
    """A resource action was blocked by a well understood condition."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


class DslError(AppError):
    """DSL execution errors."""
    pass


class UgorError(AppError):
    """Ugor server interaction errors.

    All server errors can be created with this class, since
    it will automatically switch to the appropriate subclass
    based on the response status code upon creation.
    """

    code = 500
    subclasses = {}

    def __init__(self, response, message=None):
        txt = message or response.text

        msg = f'Ugor: {txt}'
        if str(response.status_code) not in msg:
            msg += f' ({response.status_code})'

        super().__init__(msg)
        self.response = response

    def __new__(cls, response, message=None):
        # Switch class to the appropriate subclass based
        # on the response status code.
        code = response.status_code
        if code in UgorError.subclasses:
            new = super().__new__(UgorError.subclasses[code])
        else:
            new = super().__new__(cls)
            new.code = code
        return new

    def __init_subclass__(cls, *, code=None, **kwargs):
        super().__init_subclass__(**kwargs)
        # Register subclasses based on their respective
        # status code.
        UgorError.subclasses[code] = cls
        cls.code = code


class UgorError400(UgorError, code=400):
    """400 Bad Request"""
    pass


class UgorError401(UgorError, code=401):
    """401 Unauthorized"""
    pass


class UgorError403(UgorError, code=403):
    """403 Forbidden"""
    pass


class UgorError404(UgorError, code=404):
    """404 Not Found"""
    pass


class UgorError412(UgorError, code=412):
    """412 Precondition Failed"""
    pass


class UgorError440(UgorError, code=440):
    """440 No Matches"""
    pass
