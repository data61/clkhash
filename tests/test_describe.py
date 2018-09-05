import unittest
import json
import sys

try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import StringIO        # Python 3
    
from clkhash import randomnames
from clkhash.clk import generate_clks
from clkhash.describe import plot
    
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

if __name__ == "__main__":
    unittest.main()