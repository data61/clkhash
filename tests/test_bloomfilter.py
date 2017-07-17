import unittest
import random
from bitarray import bitarray

from clkhash import bloomhash as bh

__author__ = 'shardy'


class TestBloomMatcher(unittest.TestCase):

    def generate_bitarray(self, length):
        return bitarray(
            ''.join('1' if random.random() > 0.5 else '0' for _ in range(length))
        )

    def test_unigram_1(self):
        self.assertEqual(bh.unigramlist("1/2/93", '/'), ['1', '2', '9', '3'])

    def test_unigram_2(self):
        self.assertEqual(bh.unigramlist("1*2*93", '*'), ['1', '2', '9', '3'])

    def test_unigram_duplicate(self):
        self.assertEqual(bh.unigramlist("1212"), ['1', '2', '1', '2'])

    def test_unigram_1_positional(self):
        self.assertEqual(bh.unigramlist("1/2/93", '/', positional=True), ['1 1', '2 2', '3 9', '4 3'])

    def test_positional_unigram_1(self):
        self.assertEqual(bh.positional_unigrams("123"), ['1 1', '2 2', '3 3'])

    def test_positional_unigram_2(self):
        self.assertEqual(bh.positional_unigrams("1*2*"), ['1 1', '2 *', '3 2', '4 *'])

    def test_positional_unigram_duplicate(self):
        self.assertEqual(bh.positional_unigrams("111"), ['1 1', '2 1', '3 1'])

    def test_bigram_1(self):
        self.assertEqual(bh.bigramlist("steve"), [' s', 'st', 'te', 'ev', 've', 'e '])

    def test_bigram_2(self):
        self.assertEqual(bh.bigramlist("steve", 'e'), [' s', 'st', 'tv', 'v '])

    def test_bigram_duplicate(self):
        self.assertEqual(bh.bigramlist("abab"), [' a', 'ab', 'ba', 'ab', 'b '])


if __name__ == '__main__':
    unittest.main()
