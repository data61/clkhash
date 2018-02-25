#!/usr/bin/env python3.4

import unittest
import pytest
import os

from clkhash import benchmark

IS_APPVEYOR = 'APPVEYOR' in os.environ
IS_TRAVIS = 'TRAVIS' in os.environ
ON_CI = IS_APPVEYOR or IS_TRAVIS


class TestBenchmark(unittest.TestCase):

    def test_benchmarking_hash(self):
        speed = benchmark.compute_hash_speed(1000, quiet=True)
        try:
            assert speed > 100, "Hashing at less than 100 H/s"
        except AssertionError:
            if ON_CI:
                pytest.mark.xfail(ON_CI, reason="CI have inconsistent and weak muscles...")
            else:
                raise
