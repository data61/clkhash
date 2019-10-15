import base64
import unittest

from future.builtins import zip

from clkhash.bloomfilter import stream_bloom_filters
from clkhash.field_formats import FieldHashingProperties, StringSpec
from clkhash.key_derivation import DEFAULT_KEY_SIZE, generate_key_lists, hkdf
from clkhash.schema import Schema
from clkhash import comparators


class TestKeyDerivation(unittest.TestCase):

    def test_kdf(self):
        master_secret = 'No, I am your father'.encode()
        for num_keys in (1, 10, 50):
            for key_size in (2, 20):
                keys = hkdf(master_secret, num_keys, key_size=key_size)
                self.assertEqual(len(keys), num_keys)
                for key in keys:
                    self.assertEqual(len(key), key_size)

    def test_generate_key_lists(self):
        master_secret = "No, I am your fatherNo... that's not true! That's impossible!".encode()
        for num_keys in (1, 10):
            key_lists = generate_key_lists(master_secret, num_keys)
            self.assertEqual(len(key_lists), num_keys)
            for l in key_lists:
                self.assertEqual(len(l), 2)
            for key in key_lists[0]:
                self.assertEqual(len(key), DEFAULT_KEY_SIZE,
                                 msg='key should be of size '
                                     '"default_key_size"')

    def test_fail_generate_key_lists(self):
        with self.assertRaises(TypeError):
            generate_key_lists(True, 10)

    def test_nacl(self):
        master_secret = 'No, I am your father'.encode()
        keys_1 = hkdf(master_secret, 5, salt=b'and pepper')
        keys_2 = hkdf(master_secret, 5, salt=b'and vinegar')
        for k1, k2 in zip(keys_1, keys_2):
            self.assertNotEqual(k1, k2,
                                msg='using different salts should result in '
                                    'different keys')

    def test_compare_to_legacy(self):
        # Identifier: 'ANY freetext'

        fhp = FieldHashingProperties(
            comparator=comparators.get_comparator({'type': 'ngram', 'n': 2}),
            hash_type='doubleHash',
            k=10
        )

        schema = Schema(
            l=1024,
            kdf_info=base64.b64decode('c2NoZW1hX2V4YW1wbGU='),
            kdf_key_size=64,
            kdf_salt=base64.b64decode(
                'SCbL2zHNnmsckfzchsNkZY9XoHk96P'
                '/G5nUBrM7ybymlEFsMV6PAeDZCNp3rfNUPCtLDMOGQHG4pCQpfhiHCyA=='),
            fields=[StringSpec(identifier='ANY text {}'.format(i + 1),
                               hashing_properties=fhp)
                    for i in range(4)]
        )

        row = ['Bobby', 'Bobby', 'Bobby', 'Bobby']
        master_secret = "No, I am your father. No... that's not true! That's impossible!".encode()
        keys_hkdf = generate_key_lists(master_secret, len(row), kdf='HKDF')
        keys_legacy = generate_key_lists(master_secret, len(row),
                                         kdf='legacy')
        bloom_hkdf = next(stream_bloom_filters([row], keys_hkdf, schema))
        bloom_legacy = next(stream_bloom_filters([row], keys_legacy, schema))
        hkdf_count = bloom_hkdf[0].count()
        legacy_count = bloom_legacy[0].count()
        # lecay will map the 4 Bobbys' to the same bits, whereas hkdf will
        # map each Bobby to different bits.
        self.assertLessEqual(legacy_count,
                             fhp.k * 6)  # 6 bi-grams
        self.assertLess(legacy_count, hkdf_count)
        self.assertLessEqual(hkdf_count, len(row) * legacy_count)

    def test_wrong_kdf(self):
        with self.assertRaises(ValueError):
            generate_key_lists(b'0', 1, kdf='breakMe')

    def test_wrong_hash_function(self):
        with self.assertRaises(ValueError):
            hkdf('foo'.encode('ascii'),
                 3,
                 hash_algo='obviously_unsupported')
