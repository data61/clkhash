import base64
import unittest
import os
from math import sqrt

from clkhash import bloomfilter, clk, randomnames
from clkhash.key_derivation import generate_key_lists
from clkhash.schema import Schema
from clkhash.hashing_properties import HashingProperties
from clkhash.field_formats import FieldHashingPropertiesV1, StringSpec
from clkhash.serialization import deserialize_bitarray


class OnlineVariance(object):
    """
    Welford's algorithm computes the sample variance incrementally.
    From: https://stackoverflow.com/questions/5543651/computing-standard-deviation-in-a-stream
    """

    def __init__(self, iterable=None, ddof=1):
        self.ddof, self.n, self.mean, self.M2 = ddof, 0, 0.0, 0.0
        if iterable is not None:
            for datum in iterable:
                self.include(datum)

    def include(self, datum):
        self.n += 1
        self.delta = datum - self.mean
        self.mean += self.delta / self.n
        self.M2 += self.delta * (datum - self.mean)

    @property
    def variance(self):
        return self.M2 / (self.n - self.ddof)

    @property
    def std(self):
        return sqrt(self.variance)


TEST_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), 'testdata')

def _test_data_file_path(file_name):
    return os.path.join(TEST_DATA_DIRECTORY, file_name)

def _test_schema(file_name):
    with open(_test_data_file_path(file_name)) as f:
        return Schema.from_json_file(f)


class TestV2(unittest.TestCase):

    def test_compare_v1_and_v2(self):
        pii = randomnames.NameList(100).names
        schema_v1 = randomnames.NameList.SCHEMA
        # this v2 schema should be equivalent to the above v1 schema
        schema_v2 = _test_schema('randomnames-schema-v2.json')
        keys = ('secret', 'sshh')
        for clkv1, clkv2 in zip(clk.generate_clks(pii, schema_v1, keys), clk.generate_clks(pii, schema_v2, keys)):
            self.assertEqual(clkv1, clkv2)

    def test_compare_k_and_num_bits(self):
        pii = randomnames.NameList(100).names
        keys = ('secret', 'sshh')
        def stats(schema):
            counts = (deserialize_bitarray(clk).count() for clk in clk.generate_clks(pii, schema, keys))
            ov = OnlineVariance(counts)
            return ov.mean, ov.std

        schema_k = _test_schema('randomnames-schema-v2.json')
        mean_k, std_k = stats(schema_k)
        print('test_compare_k_and_num_bits k: ', mean_k, std_k)

        schema_num_bits = _test_schema('randomnames-schema-num-bits-v2.json')
        mean_num_bits, std_num_bits = stats(schema_num_bits)
        print('test_compare_k_and_num_bits num_bits: ', mean_num_bits, std_num_bits)
        # self.assertGreater(std_k, std_num_bits)

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
