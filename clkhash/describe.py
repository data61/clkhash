# -*- coding: utf-8 -*-

import json
from clkhash.backports import raise_from
from bashplotlib.histogram import plot_hist
from clkhash.serialization import deserialize_bitarray


class DescribeError(Exception):
    """ The user provided CLK JSON is invalid.
    """


def plot(clk_json):
    try:
        # data was writen with: json.dump({'clks': clk_data}, output); so ...
        clks = json.load(clk_json)['clks']
    except ValueError as e:  # In Python 3 we can be more specific
        # with json.decoder.JSONDecodeError,
        # but that doesn't exist in Python 2.
        msg = 'The input is not a valid JSON file.'
        raise_from(DescribeError(msg), e)
        
    if len(clks) == 0:
        msg = 'No clks found'
        raise DescribeError(msg)

    popcounts = [deserialize_bitarray(clk).count() for clk in clks]
    plot_hist(popcounts, bincount=60, title='popcounts', xlab=True, showSummary=True)
