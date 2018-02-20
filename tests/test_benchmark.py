#!/usr/bin/env python3.4

import unittest
import os

from clkhash import benchmark


class TestBenchmark(unittest.TestCase):

    @unittest.skipIf("TRAVIS" in os.environ and os.environ['TRAVIS'] == 'true',
                     "Travis has no muscles to speak of...")
    def test_benchmarking_hash(self):
        speed = benchmark.compute_hash_speed(1000, quiet=True)
        self.assertGreater(speed, 100, "Hashing at less than 100 H/s")

