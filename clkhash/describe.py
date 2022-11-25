class DescribeError(Exception):
    """ The user provided CLK data is invalid.
    """


def get_encoding_popcounts(clks):
    """

    Often shown as a histogram.

    :param clks: An iterable of CLK encodings.
    :return: An array of integers - the number of bits set for each encoding.
    """

    if len(clks) == 0:
        msg = 'No clks found'
        raise DescribeError(msg)
    try:
        return [clk.count() for clk in clks]
    except Exception as e:
        raise DescribeError("Failed to deserialize encodings") from e
