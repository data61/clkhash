import unittest
from clkhash import randomnames, bloomfilter
from clkhash.key_derivation import generate_key_lists
from clkhash.identifier_types import IdentifierType


class TestNamelistHashable(unittest.TestCase):
    def test_namelist_hashable(self):
        namelist = randomnames.NameList(1000)
        s1, s2 = namelist.generate_subsets(100, 0.8)

        self.assertEqual(len(s1), 100)
        self.assertEqual(len(s2), 100)

        bf1 = bloomfilter.calculate_bloom_filters(s1, namelist.schema_types,
                                                  generate_key_lists(('secret', 'sshh'), len(namelist.schema_types)))
        bf2 = bloomfilter.calculate_bloom_filters(s2, namelist.schema_types,
                                                  generate_key_lists(('secret', 'sshh'), len(namelist.schema_types)))

        self.assertEqual(len(bf1), 100)
        self.assertEqual(len(bf2), 100)

        # An "exact match" bloomfilter comparison:
        set1 = set([tuple(bf[0]) for bf in bf1])
        set2 = set([tuple(bf[0]) for bf in bf2])

        self.assertGreaterEqual(len(set1.intersection(set2)), 80,
                                "Expected at least 80 hashes to be exactly the same")


class TestHashingWithDifferentWeights(unittest.TestCase):
    def test_different_weights(self):
        pii = [['Deckard']]
        keys = generate_key_lists(('secret', 'sauce'), 1)
        it = [IdentifierType(weight=0)]
        bf0 = bloomfilter.calculate_bloom_filters(pii, it, keys)[0]
        it = [IdentifierType(weight=1)]
        bf1 = bloomfilter.calculate_bloom_filters(pii, it, keys)[0]
        it = [IdentifierType(weight=2)]
        bf2 = bloomfilter.calculate_bloom_filters(pii, it, keys)[0]
        it = [IdentifierType(weight=1.5)]
        bf15 = bloomfilter.calculate_bloom_filters(pii, it, keys)[0]

        self.assertEqual(bf0[0].count(), 0)
        n1 = bf1[0].count()
        n2 = bf2[0].count()
        n15 = bf15[0].count()
        self.assertGreater(n1, 0)
        self.assertGreater(n15, n1)
        self.assertGreater(n2, n15)
        self.assertLessEqual(n15, round(n1*1.5))
        self.assertLessEqual(n2, n1*2)
