#!/usr/bin/env python3

"""
Serialize bitarray to/from base64 utf-8 encoded string
"""

import base64
from bitarray import bitarray


def serialize_bitarray(ba):
    # type: (bitarray) -> str
    """Serialize a bitarray (bloomfilter)

    """
    return base64.b64encode(ba.tobytes()).decode('utf8')

def deserialize_bitarray(ser):
    # type: (str) -> bitarray
    """Deserialize a base 64 encoded string to a bitarray (bloomfilter)
    
    """
    ba = bitarray()
    ba.frombytes(base64.b64decode(ser.encode(encoding='UTF-8', errors='strict')))
    return ba
