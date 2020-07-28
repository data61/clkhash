import base64
import os
import unittest

from bitarray import frozenbitarray

from clkhash import bloomfilter, clk, randomnames, schema
from clkhash.describe import get_encoding_popcounts
from clkhash.field_formats import FieldHashingProperties, StringSpec, BitsPerTokenStrategy, BitsPerFeatureStrategy
from clkhash.key_derivation import generate_key_lists
from clkhash.schema import Schema
from clkhash.stats import OnlineMeanVariance
from clkhash.comparators import get_comparator

TEST_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), 'testdata')

bigram_tokenizer = get_comparator({'type': 'ngram', 'n': 2})

def _test_data_file_path(file_name):
    return os.path.join(TEST_DATA_DIRECTORY, file_name)


def _test_schema(file_name):
    with open(_test_data_file_path(file_name)) as f:
        return schema.from_json_file(f)


def _test_stats(pii, schema, keys):
    counts = get_encoding_popcounts(clk.generate_clks(pii, schema, keys))
    print('_test_stats: counts = ', counts)
    ov = OnlineMeanVariance()
    ov.update(counts)
    return ov.mean(), ov.std()


class TestV2(unittest.TestCase):

    def test_compare_v1_v2_and_v3(self):
        pii = randomnames.NameList(100).names
        schema_v3 = randomnames.NameList.SCHEMA
        # this v2 schema should be equivalent to the above v3 schema
        schema_v2 = _test_schema('randomnames-schema-v2.json')
        schema_v1 = _test_schema('randomnames-schema-v1.json')
        secret = 'secret'
        for clkv1, clkv2, clkv3 in zip(clk.generate_clks(pii, schema_v1, secret),
                                       clk.generate_clks(pii, schema_v2, secret),
                                       clk.generate_clks(pii, schema_v3, secret)):
            self.assertEqual(clkv1, clkv2)
            self.assertEqual(clkv1, clkv3)

    def test_compare_strategies(self):
        def mkSchema(hashing_properties):
            return Schema(
                l=1024,
                xor_folds=1,
                kdf_type='HKDF',
                kdf_hash='SHA256',
                kdf_salt=base64.b64decode(
                    'SCbL2zHNnmsckfzchsNkZY9XoHk96P'
                    '/G5nUBrM7ybymlEFsMV6PAeDZCNp3r'
                    'fNUPCtLDMOGQHG4pCQpfhiHCyA=='),
                kdf_info=base64.b64decode('c2NoZW1hX2V4YW1wbGU='),
                kdf_key_size=64,
                fields=[
                    StringSpec(
                        identifier='name',
                        hashing_properties=hashing_properties,
                        description=None,
                        case=StringSpec._DEFAULT_CASE,
                        min_length=1,
                        max_length=50
                    )
                ]
            )

        pii = [('An',), ('Fred',), ('Philhowe',), ('MuhlbachBereznyz',)]
        secret = 'secret'

        schema_k = mkSchema(FieldHashingProperties(
            encoding=FieldHashingProperties._DEFAULT_ENCODING,
            comparator=bigram_tokenizer,
            strategy=BitsPerTokenStrategy(20),
            hash_type='doubleHash'
        ))

        mean_k, std_k = _test_stats(pii, schema_k, secret)
        print('test_compare_k_and_num_bits k: ', mean_k, std_k)

        schema_num_bits = mkSchema(FieldHashingProperties(
            encoding=FieldHashingProperties._DEFAULT_ENCODING,
            comparator=bigram_tokenizer,
            strategy=BitsPerFeatureStrategy(int(round(mean_k))),
            hash_type='doubleHash'
        ))
        mean_num_bits, std_num_bits = _test_stats(pii, schema_num_bits, secret)
        print('test_compare_k_and_num_bits num_bits: ', mean_num_bits,
              std_num_bits)

        self.assertGreater(std_k, 2 * std_num_bits,
                           'Standard deviation for num_bits should be'
                           ' < half that for the equivalent k')


class TestNamelistHashable(unittest.TestCase):
    def test_namelist_hashable(self):
        namelist = randomnames.NameList(1000)
        s1, s2 = namelist.generate_subsets(100, 0.8)

        self.assertEqual(len(s1), 100)
        self.assertEqual(len(s2), 100)

        schema = randomnames.NameList.SCHEMA
        secret = 'secret'

        bf1 = clk.generate_clks(s1, schema, secret)
        bf2 = clk.generate_clks(s2, schema, secret)

        self.assertEqual(len(bf1), 100)
        self.assertEqual(len(bf2), 100)

        # An "exact match" bloomfilter comparison:
        set1 = set([frozenbitarray(bf) for bf in bf1])
        set2 = set([frozenbitarray(bf) for bf in bf2])

        self.assertGreaterEqual(
            len(set1 & set2), 80,
            "Expected at least 80 hashes to be exactly the same")


class TestHashingWithDifferentK(unittest.TestCase):
    """Used to test weights, but now field value for k incorporates the old
    weight"""

    def test_different_weights(self):
        schema = Schema(
            l=1024,
            xor_folds=0,
            kdf_hash='SHA256',
            kdf_info=base64.b64decode('c2NoZW1hX2V4YW1wbGU='),
            kdf_key_size=64,
            kdf_salt=base64.b64decode(
                'SCbL2zHNnmsckfzchsNkZY9XoHk96P'
                '/G5nUBrM7ybymlEFsMV6PAeDZCNp3rfNUPCtLDMOGQHG4pCQpfhiHCyA=='),
            kdf_type='HKDF',
            fields=[
                StringSpec(
                    identifier='some info',
                    hashing_properties=FieldHashingProperties(
                        encoding=FieldHashingProperties._DEFAULT_ENCODING,
                        comparator=bigram_tokenizer,
                        strategy=BitsPerTokenStrategy(20)
                    ),
                    description=None,
                    case=StringSpec._DEFAULT_CASE,
                    min_length=0,
                    max_length=None
                )
            ]
        )

        pii = [['Deckard']]
        keys = generate_key_lists('secret', 1)

        schema.fields[0].hashing_properties.strategy = BitsPerTokenStrategy(0)
        bf0 = next(bloomfilter.stream_bloom_filters(pii, keys, schema))

        schema.fields[0].hashing_properties.strategy = BitsPerTokenStrategy(20)
        bf1 = next(bloomfilter.stream_bloom_filters(pii, keys, schema))

        schema.fields[0].hashing_properties.strategy = BitsPerTokenStrategy(40)
        bf2 = next(bloomfilter.stream_bloom_filters(pii, keys, schema))

        schema.fields[0].hashing_properties.strategy = BitsPerTokenStrategy(30)
        bf15 = next(bloomfilter.stream_bloom_filters(pii, keys, schema))

        self.assertEqual(bf0[0].count(), 0)
        n1 = bf1[0].count()
        n2 = bf2[0].count()
        n15 = bf15[0].count()
        self.assertGreater(n1, 0)
        self.assertGreater(n15, n1)
        self.assertGreater(n2, n15)
        self.assertLessEqual(n15, round(n1 * 1.5))
        self.assertLessEqual(n2, n1 * 2)


class TestHashingWithDifferentHashFunctions(unittest.TestCase):
    """Schema allows to define the hash function on a per field basis."""

    def test_different_hash_functions(self):
        schema = Schema(
            l=1024,
            xor_folds=0,
            kdf_hash='SHA256',
            kdf_info=base64.b64decode('c2NoZW1hX2V4YW1wbGU='),
            kdf_key_size=64,
            kdf_salt=base64.b64decode(
                'SCbL2zHNnmsckfzchsNkZY9XoHk96P'
                '/G5nUBrM7ybymlEFsMV6PAeDZCNp3rfNUPCtLDMOGQHG4pCQpfhiHCyA=='),
            kdf_type='HKDF',
            fields=[
                StringSpec(
                    identifier='some info',
                    hashing_properties=FieldHashingProperties(
                        encoding=FieldHashingProperties._DEFAULT_ENCODING,
                        comparator=bigram_tokenizer,
                        strategy=BitsPerTokenStrategy(25),
                        hash_type='blakeHash'
                    ),
                    description=None,
                    case=StringSpec._DEFAULT_CASE,
                    min_length=0,
                    max_length=None
                ),
                StringSpec(
                    identifier='some other very important info',
                    hashing_properties=FieldHashingProperties(
                        encoding=FieldHashingProperties._DEFAULT_ENCODING,
                        comparator=bigram_tokenizer,
                        strategy=BitsPerTokenStrategy(25),
                        hash_type='doubleHash'
                    ),
                    description=None,
                    case=StringSpec._DEFAULT_CASE,
                    min_length=0,
                    max_length=None
                )
            ]
        )

        pii = [['Deckard', 'Cane']]
        keys = generate_key_lists('secret', 2)
        blake_field = schema.fields[0]
        double_hash_field = schema.fields[1]

        bf = next(bloomfilter.stream_bloom_filters(pii, keys, schema))

        schema.fields = [double_hash_field, blake_field]
        bf_reversed = next(bloomfilter.stream_bloom_filters(pii, keys, schema))

        self.assertNotEqual(bf[0], bf_reversed[0])
