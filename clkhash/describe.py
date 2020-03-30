# -*- coding: utf-8 -*-
from clkhash.backports import raise_from
from clkhash.serialization import deserialize_bitarray


class DescribeError(Exception):
    """ The user provided CLK data is invalid.
    """


def get_encoding_popcounts(clks):
    """

    Often shown as a histogram.

    :param clk: An iterable of CLK serialized encodings.
    :return: An array of integers - the number of bits set for each encoding.
    """

    if len(clks) == 0:
        msg = 'No clks found'
        raise DescribeError(msg)
    try:
        return [deserialize_bitarray(clk).count() for clk in clks]
    except Exception as e:
        raise_from(DescribeError("Failed to deserialize encodings"), e)
