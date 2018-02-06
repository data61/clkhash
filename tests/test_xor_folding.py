import unittest

from bitarray import bitarray

from clkhash import randomnames, bloomfilter
from clkhash.key_derivation import generate_key_lists


class TestNamelistHashableXorFolding(unittest.TestCase):
    def test_namelist_hashable_xor_folding(self):
        namelist = randomnames.NameList(1000)
        s1, s2 = namelist.generate_subsets(100, 0.8)

        self.assertEqual(len(s1), 100)
        self.assertEqual(len(s2), 100)

        last_length = None
        for fold_number in range(4):
            bf1 = bloomfilter.calculate_bloom_filters(
                s1,
                namelist.schema_types,
                generate_key_lists(('secret', 'sshh'), len(namelist.schema_types)),
                xor_folds=fold_number)
            bf2 = bloomfilter.calculate_bloom_filters(
                s2,
                namelist.schema_types,
                generate_key_lists(('secret', 'sshh'), len(namelist.schema_types)),
                xor_folds=fold_number)

            self.assertEqual(len(bf1), 100)
            self.assertEqual(len(bf2), 100)

            # An "exact match" bloomfilter comparison:
            set1 = {tuple(bf[0]) for bf in bf1}
            set2 = {tuple(bf[0]) for bf in bf2}

            if last_length is not None:
                self.assertEqual(
                    len(bf1[0][0]), (last_length + 1) // 2,
                    'Size of the hash is expected to be halved with each fold.')
            self.assertEqual(
                len({len(bf) for bf, _, _ in bf1}
                    | {len(bf) for bf, _, _ in bf2}),
                1,
                'All hash lengths are expected to be equal.')
            last_length = len(bf1[0][0])

            self.assertGreaterEqual(len(set1.intersection(set2)), 80,
                                    "Expected at least 80 hashes to be exactly the same")


class TestXorFoldingBitwise(unittest.TestCase):
    def test_xor_folding_bitwise(self):
        namelist = randomnames.NameList(1)
        key_lists = generate_key_lists(('secret', 'sshh'), len(namelist.schema_types))
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
            len(bf_original) % 2, 0,
            'Length of original Bloom filter is expected to be even.')
        self.assertEqual(
            len(bf_original), 2 * len(bf_folded),
            'Length of the folded filter should be half of the original.')

        for b_orig1, b_orig2, b_fold in zip(
                bf_original[:len(bf_original) // 2],
                bf_original[len(bf_original) // 2:],
                bf_folded):
            self.assertEqual((b_orig1 != b_orig2), b_fold,
                             'The XOR in XOR folding is not XORing.')
