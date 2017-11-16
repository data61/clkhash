

import unittest
import math
from clkhash import clk, randomnames, bloomfilter, schema


class TestNamelistHashable(unittest.TestCase):

    def test_namelist_hashable(self):
        namelist = randomnames.NameList(1000)
        s1, s2 = namelist.generate_subsets(100, 0.8)
        bf1 = bloomfilter.calculate_bloom_filters(s1, namelist.schema_types, ('secret', 'sshh'))
