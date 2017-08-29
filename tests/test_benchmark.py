#!/usr/bin/env python3.4

import unittest

from clkhash import benchmark


class TestBenchmark(unittest.TestCase):

    def test_benchmarking_hash(self):
        speed = benchmark.compute_hash_speed(1000)
        self.assertGreater(speed, 100, "Hashing at less than 100 H/s")

