from base64 import b64decode
import unittest

from clkhash.backports import int_from_bytes


class TestIntBackports(unittest.TestCase):
    def test_big_endian(self):
        self.assertEqual(
            34,
            int_from_bytes(b64decode('Ig=='.encode('ascii')), 'big'),
            msg="Int from bytes doesn't match expected value.")

        self.assertEqual(
            45673,
            int_from_bytes(
                b64decode('AAAAAAAAAACyaQ=='.encode('ascii')),
                'big'),
            msg="Int from bytes doesn't match expected value.")

        self.assertEqual(
            56789876545678987654678987654567898765456789765456787654,
            int_from_bytes(
                b64decode('AlDp+lkU/TxpNjohctiKo3IFkbpFKfjG'.encode('ascii')),
                'big'),
            msg="Int from bytes doesn't match expected value.")

    def test_little_endian(self):
        self.assertEqual(
            34,
            int_from_bytes(b64decode('Ig=='.encode('ascii')), 'little'),
            msg="Int from bytes doesn't match expected value.")

        self.assertEqual(
            45673,
            int_from_bytes(
                b64decode('abIAAAAAAAAAAA=='.encode('ascii')),
                'little'),
            msg="Int from bytes doesn't match expected value.")

        self.assertEqual(
            56789876545678987654678987654567898765456789765456787654,
            int_from_bytes(
                b64decode('xvgpRbqRBXKjithyITo2aTz9FFn66VAC'.encode('ascii')),
                'little'),
            msg="Int from bytes doesn't match expected value.")

    def test_invalid_arg(self):
        with self.assertRaises(
                ValueError,
                msg='Expected raise ValueError on invalid endianness.'):
            int_from_bytes(
                b64decode('abIAAAAAAAAAAA=='.encode('ascii')),
                'lobster')
