#!/usr/bin/env python3.4

import pytest
import unittest
import pytest
import os
import sys

from clkhash.cli import ProgressBar

IS_APPVEYOR = 'APPVEYOR' in os.environ
IS_TRAVIS = 'TRAVIS' in os.environ
IS_PY3 = sys.version_info[0] >= 3
ON_CI = IS_APPVEYOR or IS_TRAVIS


class TestProgressBar(unittest.TestCase):

    def test_progressbar(self):
        progress_bar = ProgressBar()

        # Allow closing before initialisation
        progress_bar.close()

        # Disallow callback before initialisation
        with pytest.raises(TypeError):
            progress_bar.callback(0, [0])

        progress_bar.initialise(1)
        self.assertEqual(progress_bar.pbar.disable, False)

        progress_bar.callback(1, [1])

        progress_bar.close()
        self.assertEqual(progress_bar.pbar.disable, True)
