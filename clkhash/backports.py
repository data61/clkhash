import csv
import re
import sys
import time
from datetime import datetime
from typing import AnyStr, Callable, cast, Pattern, Sequence, Text

from future.utils import raise_from as _raise_from
from mypy_extensions import Arg, DefaultNamedArg, NoReturn

try:
    int_from_bytes = int.from_bytes
except AttributeError:
    import codecs


    def _int_from_bytes(bytes, byteorder, signed=False):
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
                          _int_from_bytes)


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
    # Don't worry, this short-circuits.
    assert type(pattern) is str or type(pattern) is unicode  # type: ignore

    return re.compile(r'(?:{})\Z'.format(pattern), flags=flags)


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
                  if sys.version_info < (3, 0)
                  else csv.reader)  # Py3 with native Unicode support.

if hasattr(__builtins__, 'TimeoutError'):
    TimeoutError = __builtins__.TimeoutError    # type: type
else:
    TimeoutError = OSError

if sys.version_info > (3, 2):
    strftime = datetime.strftime
else:
    _YEAR_LEN = 4

    # Detect the unsupported '%s' format. But don't match if there's an
    # even number of '%'s before the 's' because those are all escaped.
    _illegal_s = re.compile(r'((^|[^%])(%%)*%s)')


    def _findall(text, substr):
        # Also finds overlaps
        i = 0
        while True:
            j = text.find(substr, i)
            if j == -1:
                return

            yield j
            i = j + 1


    def strftime(dt, fmt):
        # type: (datetime, Text) -> Text
        """ strftime that support years < 1900 in Python < 3.2.

            Kudos: https://github.com/ActiveState/code/blob/master/recipes/Python/306860_proleptic_Gregoridates_strftime_before/recipe-306860.py
        """
        if _illegal_s.search(fmt):
            msg = "this strftime implementation does not handle '%s'"
            raise ValueError()
        if dt.year > 1900:
            return dt.strftime(fmt)

        year = dt.year
        timetuple = dt.timetuple()
        timetuple_without_year = timetuple[1:]

        # Every 28 years the calendar repeats, except through century
        # leap years where it's 6 years.
        # For every non-leap year century, advance by
        # 6 years to get into the 28-year repeat cycle
        delta = 2000 - year
        off = 6 * (delta // 100 + delta // 400)
        year = year + off

        # `year` and `year + (2000 - year) // 28 * 28` have the same
        # layout
        year = year + (2000 - year) // 28 * 28
        # Format with a supported year and look for all occurences of
        # said year.
        year_str = str(year)
        assert len(year_str) == _YEAR_LEN
        s1 = time.strftime(fmt, (year,) + timetuple_without_year)
        sites1 = set(_findall(s1, year_str))

        # Format with another supported year and look again for all
        # occurences of that year.
        year_p28_str = str(year + 28)
        assert len(year_p28_str) == _YEAR_LEN
        s2 = time.strftime(fmt, (year + 28,) + timetuple_without_year)
        sites2 = set(_findall(s2, year_p28_str))

        # Where those coincide is where the year goes according to our
        # format.
        sites = sites1 & sites2

        # We found the year. Now we replace.
        s = s1
        syear = '{:04}'.format(dt.year)
        assert len(syear) == _YEAR_LEN
        for site in sites:
            s = s[:site] + syear + s[site + _YEAR_LEN:]
        return s

# Help MyPy understand that this always throws.
raise_from = cast(Callable[[BaseException, BaseException], NoReturn],
                  _raise_from)
