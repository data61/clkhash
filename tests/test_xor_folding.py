from copy import copy
import random
import unittest

from bitarray import bitarray
from future.builtins import zip

from clkhash import randomnames, bloomfilter
from clkhash.key_derivation import generate_key_lists
from clkhash.schema import Schema


try:
    to_bytes = int.to_bytes
except AttributeError:
    # We are in Python 2.
    def to_bytes(n,            # int
                 length,       # int
                 endianess,    # str
                 signed=False  # DefaultNamedArg(bool, 'signed')
                 ):
        # type (...) -> bytes
        if signed:
            raise ValueError(
                "This dirty backport of int.to_bytes doesn't support signed "
                'integers. Implement it yourself, or better yet, switch to '
                'Python 3.')
            # Kudos: https://stackoverflow.com/a/20793663
        # With modifications for style.
        hex_str = '{:X}'.format(n)
        if len(hex_str) > length * 2:
            raise OverflowError('int too big to convert')
        b = hex_str.zfill(length * 2).decode('hex')
        if endianess == 'big':
            return b
        elif endianess == 'little':
            return b[::-1]
        else:
            raise ValueError("byteorder must be either 'little' or 'big'")


def random_bitarray(length,    # type: int
                    seed=None  # type: int
                    ):
    # type: (...) -> bitarray
    random.seed(seed)
    random_bits = random.getrandbits(length)

    ba = bitarray()
    ba.frombytes(to_bytes(random_bits, (length + 7) // 8, 'big'))
    return ba[-length:]


class TestXorFolding(unittest.TestCase):
    def test_xor_folding_length(self):
        ba = random_bitarray(1024, seed=0)
        self.assertEqual(
            len(bloomfilter.fold_xor(ba, folds=0)),
            1024,
            'Length should be the same after zero folds.')
        self.assertEqual(
            len(bloomfilter.fold_xor(ba, folds=1)),
            512,
            'Length should be halved after one fold.')
        self.assertEqual(
            len(bloomfilter.fold_xor(ba, folds=2)),
            256,
            'Length should be one quarter after two folds.')
        self.assertEqual(
            len(bloomfilter.fold_xor(ba, folds=3)),
            128,
            'Length should be one eighth after two folds.')

        ba = random_bitarray(98, seed=1)
        self.assertEqual(
            len(bloomfilter.fold_xor(ba, folds=0)),
            98,
            'Length should be the same after zero folds.')
        self.assertEqual(
            len(bloomfilter.fold_xor(ba, folds=1)),
            49,
            'Length should be halved after one fold.')
        with self.assertRaises(
                ValueError,
                msg=('Should raise ValueError when trying to fold filter of '
                     'odd length.')):
            bloomfilter.fold_xor(ba, folds=2)

        ba = random_bitarray(25, seed=2)
        self.assertEqual(
            len(bloomfilter.fold_xor(ba, folds=0)),
            25,
            'Length should be the same after zero folds.')
        with self.assertRaises(
                ValueError,
                msg=('Should raise ValueError when trying to fold filter of '
                     'odd length.')):
            bloomfilter.fold_xor(ba, folds=1)
        with self.assertRaises(
                ValueError,
                msg=('Should raise ValueError when trying to fold filter of '
                     'odd length.')):
            bloomfilter.fold_xor(ba, folds=2)

    def test_xor_folding_bits(self):
        ba = random_bitarray(1024, seed=0)
        ba_folded_once = bloomfilter.fold_xor(ba, folds=1)
        for bit_half1, bit_half2, bit_folded in zip(
                ba[:512], ba[512:], ba_folded_once):
            self.assertEqual(
                bit_folded,
                bit_half1 != bit_half2,
                'XOR folding is not XORing once.')

        ba_folded_twice = bloomfilter.fold_xor(ba, folds=2)
        for bit_quarter1, bit_quarter2, bit_quarter3, bit_quarter4, \
                bit_folded in zip(ba[:256], ba[256:512], ba[512:768], ba[768:],
                                  ba_folded_twice):
            self.assertEqual(
                bit_folded,
                (bit_quarter1 != bit_quarter2)
                    != (bit_quarter3 != bit_quarter4),
                'XOR folding is not XORing twice.')

    def test_xor_folding_integration(self):
        namelist = randomnames.NameList(1)
        schema_0 = namelist.SCHEMA
        assert schema_0.xor_folds == 0

        schema_1 = copy(schema_0)
        schema_1.xor_folds = 1
        schema_1.l //= 2

        key_lists = generate_key_lists('secret',
                                       len(namelist.schema_types))
        bf_original, _, _ = next(bloomfilter.stream_bloom_filters(
            namelist.names,
            key_lists,
            schema_0))
        bf_folded, _, _ = next(bloomfilter.stream_bloom_filters(
            namelist.names,
            key_lists,
            schema_1))

        self.assertEqual(
            bf_folded,
            bf_original[:len(bf_original) // 2]
                ^ bf_original[len(bf_original) // 2:],
            'Folded filter is not an XOR of the two halves of the original.')
