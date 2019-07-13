import unittest

from clkhash.field_formats import FieldHashingProperties
from clkhash.tokenizer import get_tokenizer

__author__ = 'shardy'

# some tokenizers

p1_20 = get_tokenizer(
    FieldHashingProperties(ngram=1, k=20)
)

p2_20 = get_tokenizer(
    FieldHashingProperties(ngram=2, k=20)
)

p1_20_true = get_tokenizer(
    FieldHashingProperties(ngram=1, k=20, positional=True)
)

dummy = get_tokenizer(None)

class TestTokenizer(unittest.TestCase):

    def test_unigram_1(self):
        self.assertEqual(list(p1_20("1/2/93", ignore='/')),
                         ['1', '2', '9', '3'])

    def test_unigram_2(self):
        self.assertEqual(list(p1_20("1*2*93", ignore='*')),
                         ['1', '2', '9', '3'])

    def test_unigram_duplicate(self):
        self.assertEqual(list(p1_20("1212")),
                         ['1', '2', '1', '2'])

    def test_unigram_1_positional(self):
        self.assertEqual(list(p1_20_true("1/2/93", ignore='/')),
                         ['1 1', '2 2', '3 9', '4 3'])

    def test_positional_unigram_1(self):
        self.assertEqual(list(p1_20_true("123")),
                         ['1 1', '2 2', '3 3'])

    def test_positional_unigram_2(self):
        self.assertEqual(list(p1_20_true("1*2*")),
                         ['1 1', '2 *', '3 2', '4 *'])

    def test_positional_unigram_duplicate(self):
        self.assertEqual(list(p1_20_true("111")),
                         ['1 1', '2 1', '3 1'])

    def test_bigram_1(self):
        self.assertEqual(list(p2_20("steve")),
                         [' s', 'st', 'te', 'ev', 've', 'e '])

    def test_bigram_2(self):
        self.assertEqual(list(p2_20("steve", ignore='e')),
                         [' s', 'st', 'tv', 'v '])

    def test_bigram_duplicate(self):
        self.assertEqual(list(p2_20("abab")),
                         [' a', 'ab', 'ba', 'ab', 'b '])

    def test_invalid_n(self):
        fhp = FieldHashingProperties(ngram=2, k=20, positional=True)
        fhp.ngram = -6
        with self.assertRaises(
                ValueError,
                msg='Expected raise ValueError on invalid n.'):
            tok = get_tokenizer(fhp)
            tok('prawn')

    def test_dummy(self):
        self.assertEqual(list(dummy('jobs')), [])

    def test_empty_input(self):
        self.assertEqual(list(p1_20("")), [])
        self.assertEqual(list(p1_20_true("")), [])
        self.assertEqual(list(p2_20("")), [])
