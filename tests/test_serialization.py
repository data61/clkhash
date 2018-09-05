import random
import unittest

from bitarray import bitarray
from math import ceil

from clkhash.serialization import serialize_bitarray, deserialize_bitarray

def randomBitarray(numBytes):
    ba = bitarray()
    ba.frombytes(random.getrandbits(numBytes * 8).to_bytes(numBytes, byteorder='big'))
    return ba
    
class TestSerialization(unittest.TestCase):
    def test_ser_deser_inverse(self):
        numBytes = 128
        ba = randomBitarray(numBytes)
        
        ser = serialize_bitarray(ba)
        # https://stackoverflow.com/questions/4715415/base64-what-is-the-worst-possible-increase-in-space-usage
        self.assertEqual(len(ser), ceil(numBytes/3) * 4)

        des = deserialize_bitarray(ser)
        self.assertEqual(ba, des)


