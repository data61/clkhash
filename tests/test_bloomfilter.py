import unittest
from clkhash.bloomfilter import double_hash_encode_ngrams, blake_encode_ngrams
import random
from copy import copy


class TestEncoding(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ngrams = ['a', 'b', 'c', 'd', 'e']
        cls.key_sha1 = bytearray(random.getrandbits(8) for _ in range(32))
        cls.key_md5 = bytearray(random.getrandbits(8) for _ in range(32))
        cls.k = 10

    def test_double_hash_encoding(self):
        bf = double_hash_encode_ngrams(self.ngrams, self.key_sha1, self.key_md5, self.k, 1024)
        self._test_bit_range(bf.count(), self.k, len(self.ngrams))

    def test_blake_encoding(self):
        bf = blake_encode_ngrams(self.ngrams, self.key_sha1, self.k, 1024)
        self._test_bit_range(bf.count(), self.k, len(self.ngrams))

    def _test_bit_range(self, bits_set, k, num_ngrams):
        self.assertLessEqual(bits_set, num_ngrams * k)
        self.assertGreater(bits_set, k)

    def test_blake_encoding_not_power_of_2(self):
        with self.assertRaises(ValueError):
            blake_encode_ngrams(self.ngrams, self.key_sha1, self.k, 1023)
        with self.assertRaises(ValueError):
            blake_encode_ngrams(self.ngrams, self.key_sha1, self.k, 1025)

    def test_order_of_ngrams(self):
        self._test_order_of_ngrams(
            lambda ngrams: blake_encode_ngrams(ngrams, self.key_sha1, self.k, 1024),
            copy(self.ngrams))
        self._test_order_of_ngrams(
            lambda ngrams: double_hash_encode_ngrams(ngrams, self.key_sha1, self.key_md5, self.k, 1024),
            copy(self.ngrams))

    def _test_order_of_ngrams(self, enc_function, ngrams):
        bf1 = enc_function(ngrams)
        random.shuffle(ngrams)
        bf2 = enc_function(ngrams)
        self.assertEqual(bf1, bf2)
