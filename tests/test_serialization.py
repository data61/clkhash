import os
import unittest

from bitarray import bitarray
from math import ceil

from clkhash.serialization import serialize_bitarray, deserialize_bitarray


def generate_random_bitarray(num_bytes):
    a = bitarray()
    a.frombytes(os.urandom(num_bytes))
    return a


class TestSerialization(unittest.TestCase):
    def test_ser_deser_inverse(self):
        num_bytes = 128
        ba = generate_random_bitarray(num_bytes)
        
        ser = serialize_bitarray(ba)
        # https://stackoverflow.com/questions/4715415/base64-what-is-the-worst-possible-increase-in-space-usage
        self.assertEqual(len(ser), ceil(num_bytes/3.0) * 4)

        des = deserialize_bitarray(ser)
        self.assertEqual(ba, des)
