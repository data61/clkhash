import csv
from typing import AnyStr, Callable, cast, Pattern, Sequence
import re
import sys
import time
from datetime import datetime
from typing import Text

from future.utils import raise_from as __raise_from
from mypy_extensions import Arg, DefaultNamedArg, NoReturn


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


if sys.version_info > (3, 2):
    def strftime(dt, fmt):
        # type: (datetime, Text) -> Text
        return dt.strftime(fmt)
else:
    # remove the unsupposed "%s" command.  But don't
    # do it if there's an even number of %s before the s
    # because those are all escaped.  Can't simply
    # remove the s because the result of
    #  %sY
    # should be %Y if %s isn't supported, not the
    # 4 digit year.
    _illegal_s = re.compile(r"((^|[^%])(%%)*%s)")


    def _findall(text, substr):
        # Also finds overlaps
        sites = []
        i = 0
        while 1:
            j = text.find(substr, i)
            if j == -1:
                break
            sites.append(j)
            i = j + 1
        return sites

    def strftime(dt, fmt):
        # type: (datetime, Text) -> Text
        """ sensible version of strftime for python < 3.2. The one from the standard library does not support years < 1900.
        Kudos: https://github.com/ActiveState/code/blob/master/recipes/Python/306860_proleptic_Gregoridates_strftime_before/recipe-306860.py

        # Every 28 years the calendar repeats, except through century leap
        # years where it's 6 years.  But only if you're using the Gregorian
        # calendar.  ;)
        """
        if _illegal_s.search(fmt):
            raise TypeError("This strftime implementation does not handle %s")
        if dt.year > 1900:
            return dt.strftime(fmt)

        year = dt.year
        # For every non-leap year century, advance by
        # 6 years to get into the 28-year repeat cycle
        delta = 2000 - year
        off = 6 * (delta // 100 + delta // 400)
        year = year + off

        # Move to around the year 2000
        year = year + ((2000 - year) // 28) * 28
        timetuple = dt.timetuple()
        s1 = time.strftime(fmt, (year,) + timetuple[1:])
        sites1 = _findall(s1, str(year))

        s2 = time.strftime(fmt, (year + 28,) + timetuple[1:])
        sites2 = _findall(s2, str(year + 28))

        sites = []
        for site in sites1:
            if site in sites2:
                sites.append(site)

        s = s1
        syear = "%4d" % (dt.year,)
        for site in sites:
            s = s[:site] + syear + s[site + 4:]
        return s


# Help MyPy understand that this always throws.
raise_from = cast(Callable[[Exception, Exception], NoReturn], __raise_from)
