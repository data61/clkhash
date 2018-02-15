from typing import AnyStr, Callable, cast, Pattern, Sequence
import re

from mypy_extensions import Arg, DefaultNamedArg


try:
    int_from_bytes = int.from_bytes
except AttributeError:
    import codecs
    def __int_from_bytes(bytes, byteorder, signed=False):
        # type: (Sequence[int], str, bool) -> int
        """ Emulate Python 3's int.from_bytes.

            Kudos: https://stackoverflow.com/a/30403242 (with
            modifications)

            :param bytes_: The bytes to turn into an `int`.
            :param byteorder: Either `'big'` or `'little'`.
        """
        if signed:
            raise NotImplementedError(
                "Signed integers are not currently supported in this "
                "backport.")

        if byteorder == 'big':
            pass
        elif byteorder == 'little':
            bytes_ = bytes_[::-1]
        else:
            raise ValueError("byteorder must be either 'little' or 'big'")

        hex_str = codecs.encode(bytes_, 'hex')  # type: ignore
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
