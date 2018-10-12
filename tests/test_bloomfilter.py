import random
import unittest
from copy import copy

from bitarray import bitarray
from future.builtins import range

from clkhash.bloomfilter import (blake_encode_ngrams,
                                 double_hash_encode_ngrams,
                                 double_hash_encode_ngrams_non_singular,
                                 hashing_function_from_properties)
from clkhash.field_formats import FieldHashingProperties


class TestEncoding(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ngrams = ['a', 'b', 'c', 'd', 'e']
        cls.key_sha1 = bytearray(random.getrandbits(8) for _ in range(32))
        cls.key_md5 = bytearray(random.getrandbits(8) for _ in range(32))
        cls.k = 10

    def test_double_hash_encoding(self):
        bf = double_hash_encode_ngrams(self.ngrams,
                                       (self.key_sha1, self.key_md5), self.k,
                                       1024, 'ascii')
        self._test_bit_range(bf.count(), self.k, len(self.ngrams))

    def test_blake_encoding(self):
        bf = blake_encode_ngrams(self.ngrams, (self.key_sha1,), self.k, 1024,
                                 'ascii')
        self._test_bit_range(bf.count(), self.k, len(self.ngrams))

    def test_double_hash_encoding_non_singular(self):
        bf = double_hash_encode_ngrams_non_singular(self.ngrams, (
            self.key_sha1, self.key_md5), self.k, 1024, 'ascii')
        self._test_bit_range(bf.count(), self.k, len(self.ngrams))

    def _test_bit_range(self, bits_set, k, num_ngrams):
        self.assertLessEqual(bits_set, num_ngrams * k)
        self.assertGreater(bits_set, k)

    def test_blake_encoding_not_power_of_2(self):
        with self.assertRaises(ValueError):
            blake_encode_ngrams(self.ngrams, (self.key_sha1,), self.k, 1023,
                                'ascii')
        with self.assertRaises(ValueError):
            blake_encode_ngrams(self.ngrams, (self.key_sha1,), self.k, 1025,
                                'ascii')

    def test_order_of_ngrams(self):
        self._test_order_of_ngrams(
            lambda ngrams: blake_encode_ngrams(ngrams, (self.key_sha1,),
                                               self.k, 1024, 'ascii'),
            copy(self.ngrams))
        self._test_order_of_ngrams(
            lambda ngrams: double_hash_encode_ngrams(ngrams, (
                self.key_sha1, self.key_md5), self.k, 1024, 'ascii'),
            copy(self.ngrams))
        self._test_order_of_ngrams(
            lambda ngrams: double_hash_encode_ngrams_non_singular(ngrams, (
                self.key_sha1, self.key_md5), self.k, 1024, 'ascii'),
            copy(self.ngrams))

    def _test_order_of_ngrams(self, enc_function, ngrams):
        bf1 = enc_function(ngrams)
        random.shuffle(ngrams)
        bf2 = enc_function(ngrams)
        self.assertEqual(bf1, bf2)

    def test_double_hash_singularity(self):
        singular_ngrams = ["635", "1402"]
        non_singular_ngrams = ["666", "1401"]
        k = 20
        for ngram in singular_ngrams:
            bf = double_hash_encode_ngrams([ngram], (b'secret1', b'secret2'),
                                           k, 1024, 'ascii')
            self.assertEqual(bf.count(), 1)
            bf_ns = double_hash_encode_ngrams_non_singular([ngram], (
                b'secret1', b'secret2'), k, 1024, 'ascii')
            self.assertGreater(bf_ns.count(), 1)
            self.assertNotEqual(bf, bf_ns)
        for ngram in non_singular_ngrams:
            bf = double_hash_encode_ngrams([ngram], (b'secret1', b'secret2'),
                                           k, 1024, 'ascii')
            self.assertGreater(bf.count(), 1)
            bf_ns = double_hash_encode_ngrams_non_singular([ngram], (
                b'secret1', b'secret2'), k, 1024, 'ascii')
            self.assertGreater(bf_ns.count(), 1)
            self.assertEqual(bf, bf_ns)


class TestNgramEncodings(unittest.TestCase):
    def test_from_properties_invalid_hash(self):
        # <- this is invalid.
        fhp = FieldHashingProperties(ngram=2, k=30,
                                     hash_type='jakubHash')
        with self.assertRaises(
                ValueError,
                msg='Expected ValueError on invalid encoding.'):
            hashing_function_from_properties(fhp)


def randomBitarray(numBytes):
    ba = bitarray()
    ba.frombytes(
        random.getrandbits(numBytes * 8).to_bytes(numBytes, byteorder='big'))
    return ba
