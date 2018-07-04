# Runtime functions for compiled messages

import six

from datetime import date, datetime
from decimal import Decimal


text_type = six.text_type


def handle_argument(arg, name, errors):
    if isinstance(arg,
                  (int, float, Decimal,
                   date, datetime,
                   text_type)):
        return arg
    errors.append(TypeError("Unsupported external type: {0}, {1}"
                            .format(name, type(arg))))
    return name