import base64
import unittest

from clkhash.bloomfilter import stream_bloom_filters
from clkhash.key_derivation import hkdf, generate_key_lists, DEFAULT_KEY_SIZE, HKDFconfig
from clkhash.schema import GlobalHashingProperties, Schema
from clkhash.field_formats import FieldHashingProperties, StringSpec

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
        schema = Schema(
            version=1,
            hashing_globals=GlobalHashingProperties(
                k=10,
                kdf_hash='SHA256',
                kdf_info=base64.b64decode('c2NoZW1hX2V4YW1wbGU='),
                kdf_key_size=64,
                kdf_salt=base64.b64decode('SCbL2zHNnmsckfzchsNkZY9XoHk96P/G5nUBrM7ybymlEFsMV6PAeDZCNp3rfNUPCtLDMOGQHG4pCQpfhiHCyA=='),
                kdf_type='HKDF',
                l=1024,
                type='double hash',
                xor_folds=0
            ),
            fields=[
                StringSpec(
                    identifier='ANY text 1',
                    hashing_properties=FieldHashingProperties(
                        encoding=FieldHashingProperties.DEFAULT_ENCODING,
                        ngram=2,
                        positional=False,
                        weight=1
                    ),
                    description=None,
                    case=StringSpec.DEFAULT_CASE,
                    min_length=0,
                    max_length=None
                ),
                StringSpec(
                    identifier='ANY text 2',
                    hashing_properties=FieldHashingProperties(
                        encoding=FieldHashingProperties.DEFAULT_ENCODING,
                        ngram=2,
                        positional=False,
                        weight=1
                    ),
                    description=None,
                    case=StringSpec.DEFAULT_CASE,
                    min_length=0,
                    max_length=None
                ),
                StringSpec(
                    identifier='ANY text 3',
                    hashing_properties=FieldHashingProperties(
                        encoding=FieldHashingProperties.DEFAULT_ENCODING,
                        ngram=2,
                        positional=False,
                        weight=1
                    ),
                    description=None,
                    case=StringSpec.DEFAULT_CASE,
                    min_length=0,
                    max_length=None
                ),
                StringSpec(
                    identifier='ANY text 4',
                    hashing_properties=FieldHashingProperties(
                        encoding=FieldHashingProperties.DEFAULT_ENCODING,
                        ngram=2,
                        positional=False,
                        weight=1
                    ),
                    description=None,
                    case=StringSpec.DEFAULT_CASE,
                    min_length=0,
                    max_length=None
                )
            ]
        )

        row = ['Bobby', 'Bobby', 'Bobby', 'Bobby']
        master_secrets = ['No, I am your father'.encode(), "No... that's not true! That's impossible!".encode()]
        keys_hkdf = generate_key_lists(master_secrets, len(row), kdf='HKDF')
        keys_legacy = generate_key_lists(master_secrets, len(row), kdf='legacy')
        bloom_hkdf = next(stream_bloom_filters([row], keys_hkdf, schema))
        bloom_legacy = next(stream_bloom_filters([row], keys_legacy, schema))
        hkdf_count = bloom_hkdf[0].count()
        legacy_count = bloom_legacy[0].count()
        # lecay will map the 4 Bobbys' to the same bits, whereas hkdf will map each Bobby to different bits.
        self.assertLessEqual(legacy_count, schema.hashing_globals.k * 6) # 6 bi-grams
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
