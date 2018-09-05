import unittest
import json
import sys

from clkhash import randomnames
from clkhash.clk import generate_clks
from clkhash.describe import plot

try:
    from io import StringIO        # Python 3
except ImportError:
    from StringIO import StringIO  # Python 2
    
class TestDescribe(unittest.TestCase):
    def test_describe(self):
        size = 1000
        pii_data = randomnames.NameList(size)

        clks = generate_clks(pii_data.names, pii_data.SCHEMA, ('key1', 'key2'), validate=True)
        json_clks = json.dumps({'clks': clks})
        
        # capture stdout
        orig = sys.stdout
        out = StringIO()
        sys.stdout = out
        
        plot(StringIO(json_clks))   # clkutil describe
        sys.stdout = orig           # restore stdout for following tests
        self.assertTrue(' observations: {} '.format(size) in out.getvalue())
        # print('out = {}'.format(out.getvalue()))
