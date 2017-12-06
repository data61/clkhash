import unittest
from clkhash.key_derivation import hkdf, generate_key_lists, DEFAULT_KEY_SIZE
from clkhash.identifier_types import IdentifierType
from clkhash.bloomfilter import hbloom


class TestKeyDerivation(unittest.TestCase):

    def test_kdf(self):
        master_secret = 'No, I am your father'.encode()
        for num_keys in (1, 10, 50):
            for key_length in (2, 20):
                keys = hkdf(master_secret, num_keys, key_length)
                self.assertEqual(len(keys), num_keys)
                for key in keys:
                    self.assertEqual(len(key), key_length)

    def test_generate_key_lists(self):
        master_secrets = ['No, I am your father'.encode(), "No... that's not true! That's impossible!".encode()]
        for num_keys in (1, 10):
            key_lists = generate_key_lists(master_secrets, num_keys)
            self.assertEqual(len(key_lists), len(master_secrets))
            for l in key_lists:
                self.assertEqual(len(l), num_keys)
            for key in key_lists[0]:
                self.assertEqual(len(key), DEFAULT_KEY_SIZE, msg='key should be of size "default_key_size"')

    def test_fail_generate_key_lists(self):
        with self.assertRaises(TypeError):
            generate_key_lists([True, False], 10)

    def test_nacl(self):
        master_secret = 'No, I am your father'.encode()
        keys_1 = hkdf(master_secret, 5, salt=b'and pepper')
        keys_2 = hkdf(master_secret, 5, salt=b'and vinegar')
        for k1, k2 in zip(keys_1, keys_2):
            self.assertNotEqual(k1, k2, msg='using different salts should result in different keys')

    def test_compate_to_legacy(self):
        # Identifier: 'ANY freetext'
        schema = [IdentifierType()] * 4
        row = ['Bobby', 'Bobby', 'Bobby', 'Bobby']
        master_secrets = ['No, I am your father'.encode(), "No... that's not true! That's impossible!".encode()]
        keys_hkdf = generate_key_lists(master_secrets, len(row), algo='HKDF')
        keys_legacy = generate_key_lists(master_secrets, len(row), algo='legacy')
        bloom_hkdf = hbloom(row, keys_hkdf[0], keys_hkdf[1])
        bloom_legacy = hbloom(row, keys_legacy[0], keys_legacy[1])
        print('hkdf: {}, legacy: {}'.format(bloom_hkdf.count(), bloom_legacy.count()))

    def test_wrong_algo(self):
        with self.assertRaises(ValueError):
            generate_key_lists([b'0'], 1, algo='breakMe')
