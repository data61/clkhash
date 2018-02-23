import base64
import unittest

from clkhash import randomnames, bloomfilter
from clkhash.key_derivation import generate_key_lists
from clkhash.schema import GlobalHashingProperties, Schema
from clkhash.field_formats import FieldHashingProperties, StringSpec


class TestNamelistHashable(unittest.TestCase):
    def test_namelist_hashable(self):
        namelist = randomnames.NameList(1000)
        s1, s2 = namelist.generate_subsets(100, 0.8)

        self.assertEqual(len(s1), 100)
        self.assertEqual(len(s2), 100)

        schema = randomnames.NameList.SCHEMA
        key_lists = generate_key_lists(('secret', 'sshh'),
                                       len(schema.fields)),

        bf1 = list(bloomfilter.stream_bloom_filters(s1, key_lists, schema))
        bf1 = list(bloomfilter.stream_bloom_filters(s2, key_lists, schema))

        self.assertEqual(len(bf1), 100)
        self.assertEqual(len(bf2), 100)

        # An "exact match" bloomfilter comparison:
        set1 = set([tuple(bf[0]) for bf in bf1])
        set2 = set([tuple(bf[0]) for bf in bf2])

        self.assertGreaterEqual(len(set1.intersection(set2)), 80,
                                "Expected at least 80 hashes to be exactly the same")


class TestHashingWithDifferentWeights(unittest.TestCase):
    def test_different_weights(self):
        schema = Schema(
            version=1,
            hashing_globals=GlobalHashingProperties(
                k=30,
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
                    identifier='some info',
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

        pii = [['Deckard']]
        keys = generate_key_lists(('secret', 'sauce'), 1)

        schema.fields[0].hashing_properties.weight = 0
        bf0 = bloomfilter.calculate_bloom_filters(pii, keys, schema)[0]

        schema.fields[0].hashing_properties.weight = 1
        bf1 = bloomfilter.calculate_bloom_filters(pii, keys, schema)[0]

        schema.fields[0].hashing_properties.weight = 2
        bf2 = bloomfilter.calculate_bloom_filters(pii, keys, schema)[0]

        schema.fields[0].hashing_properties.weight = 1.5
        bf15 = bloomfilter.calculate_bloom_filters(pii, keys, schema)[0]

        self.assertEqual(bf0[0].count(), 0)
        n1 = bf1[0].count()
        n2 = bf2[0].count()
        n15 = bf15[0].count()
        self.assertGreater(n1, 0)
        self.assertGreater(n15, n1)
        self.assertGreater(n2, n15)
        self.assertLessEqual(n15, round(n1*1.5))
        self.assertLessEqual(n2, n1*2)
