import csv
from typing import AnyStr, Callable, cast, Pattern, Sequence
import re
import sys

from mypy_extensions import Arg, DefaultNamedArg


try:
    int_from_bytes = int.from_bytes
except AttributeError:
    import codecs

    def __int_from_bytes(bytes, byteorder, signed=False):
        # type: (Sequence[int], str, bool) -> int
        """ Emulate Python 3's `int.from_bytes`.

            Kudos: https://stackoverflow.com/a/30403242 (with
            modifications)

            :param bytes: The bytes to turn into an `int`.
            :param byteorder: Either `'big'` or `'little'`.
        """
        if signed:
            raise NotImplementedError(
                "Signed integers are not currently supported in this "
                "backport.")

        if byteorder == 'big':
            pass
        elif byteorder == 'little':
            bytes = bytes[::-1]
        else:
            raise ValueError("byteorder must be either 'little' or 'big'")

        hex_str = codecs.encode(bytes, 'hex')  # type: ignore
        return int(hex_str, 16)

    # Make this cast since Python 2 doesn't have syntax for default
    # named arguments. Hence, must cast so Mypy thinks it matches the
    # original function.
    int_from_bytes = cast(Callable[[Arg(Sequence[int], 'bytes'),
                                Arg(str, 'byteorder'),
                                DefaultNamedArg(bool, 'signed')],
                               int],
                      __int_from_bytes)


def re_compile_full(pattern, flags=0):
    # type: (AnyStr, int) -> Pattern
    """ Create compiled regular expression such that it matches the
        entire string. Calling re.match on the output of this function
        is equivalent to calling re.fullmatch on its input.

        This is needed to support Python 2. (On Python 3, we would just
        call re.fullmatch.)
        Kudos: https://stackoverflow.com/a/30212799

        :param pattern: The pattern to compile.
        :param flags: Regular expression flags. Refer to Python
            documentation.

        :returns: A compiled regular expression.
    """
    # A pattern of type bytes doesn't make sense in Python 3.
    assert type(pattern) is not bytes or str is bytes

    return re.compile('(?:{})\Z'.format(pattern), flags=flags)


def _utf_8_encoder(unicode_csv_data):
    return (line.encode('utf-8') for line in unicode_csv_data)


def _p2_unicode_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    """ Encode Unicode as UTF-8 and parse as CSV.

        This is needed since Python 2's `csv` doesn't do Unicode.

        Kudos: https://docs.python.org/2/library/csv.html#examples

        :param unicode_csv_data: The Unicode stream to parse.
        :param dialect: The CSV dialect to use.
        :param kwargs: Any other parameters to pass to csv.reader.

        :returns: An iterator
    """
    # Encode temporarily as UTF-8:
    utf8_csv_data = _utf_8_encoder(unicode_csv_data)

    # Now we can parse!
    csv_reader = csv.reader(utf8_csv_data, dialect=dialect, **kwargs)

    # Decode UTF-8 back to Unicode, cell by cell:
    return ([unicode(cell, 'utf-8') for cell in row] for row in csv_reader)


unicode_reader = (_p2_unicode_reader  # Python 2 with hacky workarounds.
                  if sys.version_info < (3,0)
                  else csv.reader)  # Py3 with native Unicode support.
