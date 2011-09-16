class PreconditionFailed(Exception):
    """ Raise this when we want a 412 response. """

class UnsupportedMediaType(Exception):
    """ Raise this when you want a 415 response. """
