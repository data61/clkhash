import unittest
import json
import sys

from io import StringIO
    
from clkhash import randomnames
from clkhash.clk import generate_clks
from clkhash.describe import get_encoding_popcounts, DescribeError


class TestDescribe(unittest.TestCase):

    def setUp(self):
        # capture stdout
        self.original_stdout = sys.stdout
        self.temp_std_out = StringIO()
        sys.stdout = self.temp_std_out

    def tearDown(self):
        sys.stdout = self.original_stdout  # restore stdout for following tests

    def test_describe(self):
        size = 1000
        pii_data = randomnames.NameList(size)

        clks = generate_clks(pii_data.names, pii_data.SCHEMA, 'secret', validate=True)
        counts = get_encoding_popcounts(clks)

        assert len(counts) == size

    def test_describe_no_clks(self):
        with self.assertRaises(DescribeError) as e:
            get_encoding_popcounts([])   # clkutil describe

        assert 'No clks found' in e.exception.args[0]

    def test_describe_bad_clk_type(self):
        not_json_clks = 'notclks and [not](even) array'

        with self.assertRaises(DescribeError) as e:
            get_encoding_popcounts(not_json_clks)   # clkutil describe <file>

        assert 'Failed to deserialize encodings' in e.exception.args[0]
