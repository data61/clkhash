#!/usr/bin/env python3

"""
Serialize bitarray to/from base64 utf-8 encoded string
"""

import base64
from bitarray import bitarray


def serialize_bitarray(ba: bitarray) -> str:
    """Serialize a bitarray (Bloom filter)
    Creates a base64 encoded string representation of the provided bitarray.
    """
    return base64.b64encode(ba.tobytes()).decode('utf8')


def deserialize_bitarray(ser: str) -> bitarray:
    """Deserialize a base 64 encoded string to a bitarray (Bloom filter)
    """
    ba = bitarray()
    ba.frombytes(base64.b64decode(ser.encode(encoding='UTF-8', errors='strict')))
    return ba
