import unittest
from clkhash.key_derivation import hkdf, generate_key_lists, DEFAULT_KEY_SIZE, HKDFconfig
from clkhash.identifier_types import IdentifierType
from clkhash.bloomfilter import crypto_bloom_filter


class TestKeyDerivation(unittest.TestCase):

    def test_kdf(self):
        master_secret = 'No, I am your father'.encode()
        for num_keys in (1, 10, 50):
            for key_length in (2, 20):
                keys = hkdf(HKDFconfig(master_secret), num_keys, key_length)
                self.assertEqual(len(keys), num_keys)
                for key in keys:
                    self.assertEqual(len(key), key_length)

    def test_generate_key_lists(self):
        master_secrets = ['No, I am your father'.encode(), "No... that's not true! That's impossible!".encode()]
        for num_keys in (1, 10):
            key_lists = generate_key_lists(master_secrets, num_keys)
            self.assertEqual(len(key_lists), num_keys)
            for l in key_lists:
                self.assertEqual(len(l), len(master_secrets))
            for key in key_lists[0]:
                self.assertEqual(len(key), DEFAULT_KEY_SIZE, msg='key should be of size "default_key_size"')

    def test_fail_generate_key_lists(self):
        with self.assertRaises(TypeError):
            generate_key_lists([True, False], 10)

    def test_nacl(self):
        master_secret = 'No, I am your father'.encode()
        keys_1 = hkdf(HKDFconfig(master_secret, salt=b'and pepper'), 5)
        keys_2 = hkdf(HKDFconfig(master_secret, salt=b'and vinegar'), 5)
        for k1, k2 in zip(keys_1, keys_2):
            self.assertNotEqual(k1, k2, msg='using different salts should result in different keys')

    def test_compare_to_legacy(self):
        # Identifier: 'ANY freetext'
        schema = [IdentifierType()] * 4
        row = ['Bobby', 'Bobby', 'Bobby', 'Bobby']
        master_secrets = ['No, I am your father'.encode(), "No... that's not true! That's impossible!".encode()]
        k = 10
        keys_hkdf = generate_key_lists(master_secrets, len(row), kdf='HKDF')
        keys_legacy = generate_key_lists(master_secrets, len(row), kdf='legacy')
        bloom_hkdf = crypto_bloom_filter(row, schema, keys_hkdf, k=k)
        bloom_legacy = crypto_bloom_filter(row, schema, keys_legacy, k=k)
        hkdf_count = bloom_hkdf[0].count()
        legacy_count = bloom_legacy[0].count()
        # lecay will map the 4 Bobbys' to the same bits, whereas hkdf will map each Bobby to different bits.
        self.assertLessEqual(legacy_count, k * 6) # 6 bi-grams
        self.assertLess(legacy_count, hkdf_count)
        self.assertLessEqual(hkdf_count, len(row) * legacy_count)

    def test_wrong_kdf(self):
        with self.assertRaises(ValueError):
            generate_key_lists([b'0'], 1, kdf='breakMe')

    def test_HKDFconfig_wrong_hash(self):
        with self.assertRaises(ValueError):
            HKDFconfig(b'', hash_algo='SHA0815')

    def test_HKDFconfig_wrong_type(self):
        with self.assertRaises(TypeError):
            HKDFconfig(42)

    def test_hkdf_wrong_config_type(self):
        with self.assertRaises(TypeError):
            hkdf('not your type', 1)