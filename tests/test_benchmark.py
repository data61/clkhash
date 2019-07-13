#!/usr/bin/env python3.4

import pytest
import unittest
import pytest
import os
import sys

from clkhash import benchmark
from clkhash.cli import EncodingProgressBar

IS_APPVEYOR = 'APPVEYOR' in os.environ
IS_TRAVIS = 'TRAVIS' in os.environ
IS_PY3 = sys.version_info[0] >= 3
ON_CI = IS_APPVEYOR or IS_TRAVIS


class TestBenchmark(unittest.TestCase):

    @pytest.mark.skipif(IS_APPVEYOR and IS_PY3, reason="Windows benchmarking not working on Python3")
    def test_benchmarking_hash(self):
        speed = benchmark.compute_hash_speed(1000, quiet=True)
        try:
            assert speed > 100, "Hashing at less than 100 H/s"
        except AssertionError:
            if ON_CI:
                pytest.mark.xfail(ON_CI, reason="CI have inconsistent and weak muscles...")
            else:
                raise

    @pytest.mark.skipif(IS_APPVEYOR and IS_PY3, reason="Windows benchmarking not working on Python3")
    def test_benchmark_with_progressbar(self):
        benchmark.compute_hash_speed(1000, progress_interface=EncodingProgressBar)
