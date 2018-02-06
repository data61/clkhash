import unittest
from clkhash import randomnames, bloomfilter
from clkhash.key_derivation import generate_key_lists
from clkhash.identifier_types import IdentifierType


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

            print('Size:', len(bf1[0][0]))
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
