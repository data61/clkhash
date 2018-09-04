# -*- coding: utf-8 -*-

import click
import json
from clkhash.backports import raise_from
from bashplotlib.histogram import plot_hist
from clkhash.bloomfilter import deserialize_bitarray

class DescribeError(Exception):
    """ The user provided CLK JSON is invalid.
    """

def plot(input):
    try:
        # data was writen with: json.dump({'clks': clk_data}, output); so ...
        clks = json.load(input)['clks']
    except ValueError as e:  # In Python 3 we can be more specific
        # with json.decoder.JSONDecodeError,
        # but that doesn't exist in Python 2.
        msg = 'The input is not a valid JSON file.'
        raise_from(DescribeError(msg), e)
        
    
    popcounts = [ deserialize_bitarray(clk).count() for clk in clks ]
    plot_hist(popcounts, bincount=60, xlab=True, showSummary=True)
        
    
