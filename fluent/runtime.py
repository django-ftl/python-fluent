# Runtime functions for compiled messages

from datetime import date, datetime
from decimal import Decimal

import six

from fluent.exceptions import FluentCyclicReferenceError, FluentReferenceError

from .types import FluentNone, FluentType, fluent_date, fluent_number

__all__ = ['handle_argument', 'handle_argument_null_escaper', 'handle_output', 'handle_output_null_escaper', 'FluentCyclicReferenceError', 'FluentReferenceError', 'FluentNone']


text_type = six.text_type

RETURN_TYPES = {
    'handle_argument_null_escaper': object,
    'handle_output_null_escaper': text_type,
    'FluentReferenceError': FluentReferenceError,
    'FluentNone': FluentNone,
}


def handle_argument(arg, name, output_type, locale, errors):
    if isinstance(arg, output_type):
        return arg
    elif isinstance(arg, text_type):
        return arg
    elif isinstance(arg, (int, float, Decimal)):
        return fluent_number(arg)
    elif isinstance(arg, (date, datetime)):
        return fluent_date(arg)
    errors.append(TypeError("Unsupported external type: {0}, {1}"
                            .format(name, type(arg))))
    return name


#  handle_argument specialized to null_escaper for performance
def handle_argument_null_escaper(arg, name, locale, errors):
    if isinstance(arg, text_type):
        return arg
    elif isinstance(arg, (int, float, Decimal)):
        return fluent_number(arg)
    elif isinstance(arg, (date, datetime)):
        return fluent_date(arg)
    errors.append(TypeError("Unsupported external type: {0}, {1}"
                            .format(name, type(arg))))
    return name


def handle_output(val, output_type, escaper_escape, locale, errors):
    if isinstance(val, output_type):
        return val
    elif isinstance(val, text_type):
        return escaper_escape(val)
    elif isinstance(val, FluentType):
        return escaper_escape(val.format(locale))
    else:
        # The only way for this branch to run is whem functions return
        # objects of the wrong type.
        raise TypeError("Cannot handle object {0} of type {1}"
                        .format(val, type(val).__name__))


# handle_output specialized to null_escaper for performance
def handle_output_null_escaper(val, locale, errors):
    if isinstance(val, text_type):
        return val
    elif isinstance(val, FluentType):
        return val.format(locale)
    else:
        # The only way for this branch to run is whem functions return
        # objects of the wrong type.
        raise TypeError("Cannot handle object {0} of type {1}"
                        .format(val, type(val).__name__))
