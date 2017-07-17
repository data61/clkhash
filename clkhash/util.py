#!/usr/bin/env python3.4

import os
import random
from bitarray import bitarray


def generate_bitarray(length):
    a = bitarray(endian=['little', 'big'][random.randint(0, 1)])
    a.frombytes(os.urandom(length//8))
    return a


def generate_clks(n):
    res = []
    for i in range(n):
        ba = generate_bitarray(1024)
        res.append((ba, i, ba.count()))
    return res


def popcount_vector(bitarrays):
    """
    Note, due to the overhead of converting bitarrays into
    bytes, it is more expensive to call a C implementation
    than just calling bitarray.count()
    """
    return [clk.count() for clk in bitarrays]
