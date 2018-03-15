import unittest
import random
from bitarray import bitarray

from clkhash.field_formats import FieldHashingProperties
from clkhash.tokenizer import get_tokenizer, tokenize

__author__ = 'shardy'


class TestTokenizer(unittest.TestCase):
    def test_unigram_1(self):
        properties = FieldHashingProperties(
            ngram=1,
            positional=False
        )
        self.assertEqual(list(get_tokenizer(properties)("1/2/93", ignore='/')),
                         ['1', '2', '9', '3'])

    def test_unigram_2(self):
        properties = FieldHashingProperties(
            ngram=1,
            positional=False
        )
        self.assertEqual(list(get_tokenizer(properties)("1*2*93", ignore='*')),
                         ['1', '2', '9', '3'])

    def test_unigram_duplicate(self):
        properties = FieldHashingProperties(
            ngram=1,
            positional=False
        )
        self.assertEqual(list(get_tokenizer(properties)("1212")),
                         ['1', '2', '1', '2'])

    def test_unigram_1_positional(self):
        properties = FieldHashingProperties(
            ngram=1,
            positional=True
        )
        self.assertEqual(list(get_tokenizer(properties)("1/2/93", ignore='/')),
                         ['1 1', '2 2', '3 9', '4 3'])

    def test_positional_unigram_1(self):
        properties = FieldHashingProperties(
            ngram=1,
            positional=True
        )
        self.assertEqual(list(get_tokenizer(properties)("123")),
                         ['1 1', '2 2', '3 3'])

    def test_positional_unigram_2(self):
        properties = FieldHashingProperties(
            ngram=1,
            positional=True
        )
        self.assertEqual(list(get_tokenizer(properties)("1*2*")),
                         ['1 1', '2 *', '3 2', '4 *'])

    def test_positional_unigram_duplicate(self):
        properties = FieldHashingProperties(
            ngram=1,
            positional=True
        )
        self.assertEqual(list(get_tokenizer(properties)("111")),
                         ['1 1', '2 1', '3 1'])

    def test_bigram_1(self):
        properties = FieldHashingProperties(
            ngram=2,
            positional=False
        )
        self.assertEqual(list(get_tokenizer(properties)("steve")),
                         [' s', 'st', 'te', 'ev', 've', 'e '])

    def test_bigram_2(self):
        properties = FieldHashingProperties(
            ngram=2,
            positional=False
        )
        self.assertEqual(list(get_tokenizer(properties)("steve", ignore='e')),
                         [' s', 'st', 'tv', 'v '])

    def test_bigram_duplicate(self):
        properties = FieldHashingProperties(
            ngram=2,
            positional=False
        )
        self.assertEqual(list(get_tokenizer(properties)("abab")),
                         [' a', 'ab', 'ba', 'ab', 'b '])

    def test_invalid_n(self):
        with self.assertRaises(
                ValueError,
                msg='Expected raise ValueError on invalid n.'):
            tokenize(-6, True, 'prawn')            



if __name__ == '__main__':
    unittest.main()
