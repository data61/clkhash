import base64
import unittest

from clkhash import bloomfilter, clk, randomnames
from clkhash.key_derivation import generate_key_lists
from clkhash.schema import Schema
from clkhash.hashing_properties import HashingProperties
from clkhash.field_formats import FieldHashingPropertiesV1, StringSpec


class TestNamelistHashable(unittest.TestCase):
    def test_namelist_hashable(self):
        namelist = randomnames.NameList(1000)
        s1, s2 = namelist.generate_subsets(100, 0.8)

        self.assertEqual(len(s1), 100)
        self.assertEqual(len(s2), 100)

        schema = randomnames.NameList.SCHEMA
        keys = ('secret', 'sshh')

        bf1 = clk.generate_clks(s1, schema, keys)
        bf2 = clk.generate_clks(s2, schema, keys)

        self.assertEqual(len(bf1), 100)
        self.assertEqual(len(bf2), 100)

        # An "exact match" bloomfilter comparison:
        set1 = set(bf1)
        set2 = set(bf2)

        self.assertGreaterEqual(
            len(set1 & set2), 80,
            "Expected at least 80 hashes to be exactly the same")


class TestHashingWithDifferentWeights(unittest.TestCase):
    def test_different_weights(self):
        schema = Schema(
            l=1024,
            hashing_properties=HashingProperties(k=30, hash_type='blakeHash'),
            xor_folds=0,
            kdf_hash='SHA256',
            kdf_info=base64.b64decode('c2NoZW1hX2V4YW1wbGU='),
            kdf_key_size=64,
            kdf_salt=base64.b64decode('SCbL2zHNnmsckfzchsNkZY9XoHk96P/G5nUBrM7ybymlEFsMV6PAeDZCNp3rfNUPCtLDMOGQHG4pCQpfhiHCyA=='),
            kdf_type='HKDF',
            fields=[
                StringSpec(
                    identifier='some info',
                    hashing_properties=FieldHashingPropertiesV1(
                        encoding=FieldHashingPropertiesV1._DEFAULT_ENCODING,
                        ngram=2,
                        positional=False,
                        weight=1
                    ),
                    description=None,
                    case=StringSpec._DEFAULT_CASE,
                    min_length=0,
                    max_length=None
                )
            ]
        )

        pii = [['Deckard']]
        keys = generate_key_lists(('secret',), 1)

        schema.fields[0].hashing_properties.weight = 0
        bf0 = next(bloomfilter.stream_bloom_filters(pii, keys, schema))

        schema.fields[0].hashing_properties.weight = 1
        bf1 = next(bloomfilter.stream_bloom_filters(pii, keys, schema))

        schema.fields[0].hashing_properties.weight = 2
        bf2 = next(bloomfilter.stream_bloom_filters(pii, keys, schema))

        schema.fields[0].hashing_properties.weight = 1.5
        bf15 = next(bloomfilter.stream_bloom_filters(pii, keys, schema))

        self.assertEqual(bf0[0].count(), 0)
        n1 = bf1[0].count()
        n2 = bf2[0].count()
        n15 = bf15[0].count()
        self.assertGreater(n1, 0)
        self.assertGreater(n15, n1)
        self.assertGreater(n2, n15)
        self.assertLessEqual(n15, round(n1*1.5))
        self.assertLessEqual(n2, n1*2)
