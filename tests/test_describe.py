import unittest
import json
import sys

try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import StringIO        # Python 3
    
from clkhash import randomnames
from clkhash.clk import generate_clks
from clkhash.describe import plot, DescribeError


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

        clks = generate_clks(pii_data.names, pii_data.SCHEMA, 'key', validate=True)
        json_clks = json.dumps({'clks': clks})

        plot(StringIO(json_clks))   # clkutil describe

        assert ' observations: {} '.format(size) in self.temp_std_out.getvalue()

    def test_describe_no_clks(self):
        json_clks = json.dumps({'clks': []})
        with self.assertRaises(DescribeError) as e:
            plot(StringIO(json_clks))   # clkutil describe

        assert 'No clks found' in e.exception.args[0]

    def test_describe_non_json_clks(self):
        not_json_clks = 'notclks and [not](even) json'

        with self.assertRaises(DescribeError) as e:
            plot(StringIO(not_json_clks))   # clkutil describe <file>

        assert 'not a valid JSON' in e.exception.args[0]
