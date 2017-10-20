

import unittest
import math
from clkhash import clk, randomnames, bloomfilter, schema


class TestChunks(unittest.TestCase):

    def test_e2e(self):
        namelist = randomnames.NameList(1000)
        s1, s2 = namelist.generate_subsets(100, 0.8)
        bf1 = bloomfilter.calculate_bloom_filters(s1, namelist.schema_types, ('secret', 'sshh'))

