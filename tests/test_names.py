from datetime import datetime
from io import BytesIO
import itertools
import math
import unittest

import pytest

from clkhash import randomnames as rn

__author__ = 'shardy'


class TestRandomNames(unittest.TestCase):
    def test_save_csv(self):
        bytesIO = BytesIO()
        headers = ['Name', 'Count']
        body = [('a', 1), ('b', 2)]
        rn.save_csv(body, headers, bytesIO)
        self.assertListEqual(bytesIO.getvalue().split(), ['Name,Count', 'a,1', 'b,2'])

    def test_random_date(self):
        # String as age value
        age_dist = rn.Distribution('../tests/testdata/ages_dirty.csv')
        with pytest.raises(ValueError):
            rn.random_date(2018, age_dist)

        # Ensure dates fall in range
        age_dist = rn.Distribution('../tests/testdata/ages.csv')
        start = datetime(2016, 1, 1)
        end = datetime(2019, 1, 1)

        for i in range(1000):
            self.assertGreaterEqual((rn.random_date(2018, age_dist)-start).days, 0)
            self.assertLess((rn.random_date(2018, age_dist)-end).days, 0)

    def test_distribution(self):
        # No distribution
        age_dist = None
        with pytest.raises(ValueError):
            rn.random_date(2018, age_dist)

        # File with no content
        with pytest.raises(ValueError):
            rn.Distribution('../tests/testdata/dist_empty.csv')

        # File with only headers
        with pytest.raises(ValueError):
            rn.Distribution('../tests/testdata/dist_empty_headers.csv')

        # File with non-integer count
        with pytest.raises(ValueError):
            rn.Distribution('../tests/testdata/dist_dirty.csv')

    def test_generate_subsets(self):
        nl = rn.NameList(20)
        s1, s2 = nl.generate_subsets(10, 0.8)
        counteq = 0
        for s in s1:
            for t in s2:
                if s == t:
                    counteq += 1
        self.assertEqual(counteq, 8)

    def test_generate_subsets_raises(self):
        # sz = 999
        # n = floor(sz * 1.2) = 1198
        # overlap = floor(0.8 * 999) = 799
        # notoverlap = sz - overlap = 200.
        # Thus sz + notoverlap = 1199 > n.
        sz = 999
        n = int(math.floor(sz * 1.2))
        names = rn.NameList(n)
        with pytest.raises(ValueError):
            s1, s2 = names.generate_subsets(sz, 0.8)

    def test_generate_large_subsets(self):
        nl = rn.NameList(2000)
        s1, s2 = nl.generate_subsets(1000, 0.5)
        counteq = 0
        for s in s1:
            for t in s2:
                if s[0] == t[0]:
                    counteq += 1

        self.assertEqual(counteq, 500)


class TestRandomNamesMultiparty(unittest.TestCase):
    def test_generate_subsets(self):
        nl = rn.NameList(50)
        subsets = map(set, nl.generate_subsets(10, 0.8, subsets=5))

        for s1, s2 in itertools.combinations(subsets, 2):
            self.assertEqual(len(s1 & s2), 8, msg='unexpected overlap size')

    def test_generate_subsets_raises(self):
        names = rn.NameList(15)
        with pytest.raises(ValueError):
            names.generate_subsets(10, 0.8, subsets=5)

    def test_generate_large_subsets(self):
        nl = rn.NameList(5000)
        subsets = map(set, nl.generate_subsets(1000, 0.5, subsets=3))

        for s1, s2 in itertools.combinations(subsets, 2):
            self.assertEqual(len(s1 & s2), 500, msg='unexpected overlap size')


if __name__ == '__main__':
    unittest.main()
