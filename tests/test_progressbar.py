#!/usr/bin/env python3.4

import pytest
import unittest
import pytest
import os
import sys

from clkhash import benchmark
from clkhash.cli import ProgressBar

IS_APPVEYOR = 'APPVEYOR' in os.environ
IS_TRAVIS = 'TRAVIS' in os.environ
IS_PY3 = sys.version_info[0] >= 3
ON_CI = IS_APPVEYOR or IS_TRAVIS


class TestBenchmark(unittest.TestCase):

    @pytest.mark.skipif(IS_APPVEYOR and IS_PY3, reason="Windows benchmarking not working on Python3")
    def test_progressbar(self):
        progress_bar = ProgressBar()
        benchmark.compute_hash_speed(1000, progress_bar=progress_bar)
        self.assertEqual(progress_bar.pbar.disable, True)
