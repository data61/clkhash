import random
import unittest
from copy import copy

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
        cls.ks = [ cls.k ] * len(cls.ngrams)

    def test_double_hash_encoding(self):
        bf = double_hash_encode_ngrams(self.ngrams,
                                       (self.key_sha1, self.key_md5), self.ks,
                                       1024, 'ascii')
        self._test_bit_range(bf.count(), self.k, len(self.ngrams))

    def test_blake_encoding(self):
        bf = blake_encode_ngrams(self.ngrams, (self.key_sha1,), self.ks, 1024,
                                 'ascii')
        self._test_bit_range(bf.count(), self.k, len(self.ngrams))

    def test_double_hash_encoding_non_singular(self):
        bf = double_hash_encode_ngrams_non_singular(self.ngrams, (
            self.key_sha1, self.key_md5), self.ks, 1024, 'ascii')
        self._test_bit_range(bf.count(), self.k, len(self.ngrams))

    def _test_bit_range(self, bits_set, k, num_ngrams):
        self.assertLessEqual(bits_set, num_ngrams * k)
        self.assertGreater(bits_set, k)

    def test_blake_encoding_not_power_of_2(self):
        with self.assertRaises(ValueError):
            blake_encode_ngrams(self.ngrams, (self.key_sha1,), self.ks, 1023,
                                'ascii')
        with self.assertRaises(ValueError):
            blake_encode_ngrams(self.ngrams, (self.key_sha1,), self.ks, 1025,
                                'ascii')

    def test_order_of_ngrams(self):
        self._test_order_of_ngrams(
            lambda ngrams: blake_encode_ngrams(ngrams, (self.key_sha1,),
                                               self.ks, 1024, 'ascii'),
            copy(self.ngrams))
        self._test_order_of_ngrams(
            lambda ngrams: double_hash_encode_ngrams(ngrams, (
                self.key_sha1, self.key_md5), self.ks, 1024, 'ascii'),
            copy(self.ngrams))
        self._test_order_of_ngrams(
            lambda ngrams: double_hash_encode_ngrams_non_singular(ngrams, (
                self.key_sha1, self.key_md5), self.ks, 1024, 'ascii'),
            copy(self.ngrams))

    def _test_order_of_ngrams(self, enc_function, ngrams):
        bf1 = enc_function(ngrams)
        random.shuffle(ngrams)
        bf2 = enc_function(ngrams)
        self.assertEqual(bf1, bf2)

    def test_double_hash_singularity(self):
        singular_ngrams = ["635", "1402"]
        non_singular_ngrams = ["666", "1401"]
        ks = [20]
        for ngram in singular_ngrams:
            bf = double_hash_encode_ngrams([ngram], (b'secret1', b'secret2'),
                                           ks, 1024, 'ascii')
            self.assertEqual(bf.count(), 1)
            bf_ns = double_hash_encode_ngrams_non_singular([ngram], (
                b'secret1', b'secret2'), ks, 1024, 'ascii')
            self.assertGreater(bf_ns.count(), 1)
            self.assertNotEqual(bf, bf_ns)
        for ngram in non_singular_ngrams:
            bf = double_hash_encode_ngrams([ngram], (b'secret1', b'secret2'),
                                           ks, 1024, 'ascii')
            self.assertGreater(bf.count(), 1)
            bf_ns = double_hash_encode_ngrams_non_singular([ngram], (
                b'secret1', b'secret2'), ks, 1024, 'ascii')
            self.assertGreater(bf_ns.count(), 1)
            self.assertEqual(bf, bf_ns)

    def test_bug210(self):
        # https://github.com/n1analytics/clkhash/issues/210
        common_tokens = [str(i) for i in range(65)]
        e1 = common_tokens + ['e1']          # 66 tokens
        e2 = common_tokens + ['e2a', 'e2b']  # 67 tokens
        tok_sim = 2.0 * len(common_tokens) / (len(e1) + len(e2))

        fhp = FieldHashingProperties(ngram=2, num_bits=100,
                                     hash_type='doubleHash')
        f = lambda tokens: double_hash_encode_ngrams(
            tokens,
            (self.key_sha1, self.key_md5),
            fhp.ks(len(tokens)),
            1024,
            fhp.encoding)
        b1 = f(e1)
        b2 = f(e2)
        intersect = b1 & b2
        sim = 2.0 * intersect.count() / (b1.count() + b2.count())
        # print('test_bug210: bit counts: b1 = {}, b2 = {}, intersect = {}'
        #       ', tok_sim = {}, sim = {}'
        #       .format(b1.count(),
        #               b2.count(),
        #               intersect.count(),
        #               tok_sim, sim))
        self.assertGreater(sim, 0.9 * tok_sim)
        # 0.9 to allow for some collisions


class TestNgramEncodings(unittest.TestCase):
    def test_from_properties_invalid_hash(self):
        fhp = FieldHashingProperties(
            ngram=2, k=30,
            hash_type='jakubHash'  # <- this is invalid.
        )
        with self.assertRaises(
                ValueError,
                msg='Expected ValueError on invalid encoding.'):
            hashing_function_from_properties(fhp)




