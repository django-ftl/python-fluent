from __future__ import absolute_import, unicode_literals


def identity(value):
    """
    Identity function.
    The function is also used as a sentinel value by the
    compiler for it to detect a no-op
    """
    return value


# Default string join function and sentinel value
default_string_join = ''.join


# Namespace class for default escaping (i.e. no escaping). It is used without
# instantiating, hence not capitalised as a class.
class null_escaper(object):

    def select(message_id=None, **kwargs):
        return True

    escape = identity

    mark_escaped = identity

    string_join = default_string_join


def escapers_compatible(outer_escaper, inner_escaper):
    # Messages with no escaper defined can always be used from other messages,
    # because the outer message will do the escaping, and the inner message will
    # always return a simple string which must be handle by all escapers.
    if inner_escaper is null_escaper:
        return True

    # Otherwise, however, since escapers could potentially build completely
    # different types of objects, we disallow any other mismatch.
    return outer_escaper is inner_escaper


def escaper_for_message(escapers, message_id):
    if escapers:
        for escaper in escapers:
            if escaper.select(message_id=message_id):
                return escaper

    return null_escaper