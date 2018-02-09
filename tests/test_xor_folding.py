import random
import unittest

from bitarray import bitarray
from future.builtins import zip

from clkhash import randomnames, bloomfilter
from clkhash.key_derivation import generate_key_lists


def random_bitarray(length,    # type: int
                    seed=None  # type: int
                    ):
    # type: (...) -> bitarray
    random.seed(seed)
    random_bits = random.getrandbits(length)

    ba = bitarray()
    ba.frombytes(random_bits.to_bytes((length + 7) // 8, 'big'))
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
        key_lists = generate_key_lists(('secret', 'sshh'),
                                       len(namelist.schema_types))
        (bf_original, _, _), = bloomfilter.calculate_bloom_filters(
            namelist.names,
            namelist.schema_types,
            key_lists,
            xor_folds=0)
        (bf_folded, _, _), = bloomfilter.calculate_bloom_filters(
            namelist.names,
            namelist.schema_types,
            key_lists,
            xor_folds=1)

        self.assertEqual(
            bf_folded,
            bf_original[:len(bf_original) // 2]
                ^ bf_original[len(bf_original) // 2:],
            'Folded filter is not an XOR of the two halves of the original.')
