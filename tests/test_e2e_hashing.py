

import unittest
import math
from clkhash import clk, randomnames, bloomfilter, schema


class TestNamelistHashable(unittest.TestCase):

    def test_namelist_hashable(self):
        namelist = randomnames.NameList(1000)
        s1, s2 = namelist.generate_subsets(100, 0.8)

        self.assertEqual(len(s1), 100)
        self.assertEqual(len(s2), 100)

        bf1 = bloomfilter.calculate_bloom_filters(s1, namelist.schema_types, ('secret', 'sshh'))
        bf2 = bloomfilter.calculate_bloom_filters(s2, namelist.schema_types, ('secret', 'sshh'))

        self.assertEqual(len(bf1), 100)
        self.assertEqual(len(bf2), 100)

        # An "exact match" bloomfilter comparison:
        set1 = set([tuple(bf[0]) for bf in bf1])
        set2 = set([tuple(bf[0]) for bf in bf2])

        self.assertGreaterEqual(len(set1.intersection(set2)), 80,
                                "Expected at least 80 hashes to be exactly the same")
