# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

import json
import io
import unittest

from clkhash import clk, schema


class TestChunks(unittest.TestCase):

    def test_simple_chunk(self):
        l = list(range(100))
        res = list(clk.chunks(l, 5))
        self.assertEqual(len(res), 20)
        self.assertEqual(len(res[0]), 5)

    def test_uneven_chunk(self):
        l = list(range(17))
        res = list(clk.chunks(l, 10))
        self.assertEqual([0,1,2,3,4,5,6,7,8,9], res[0])
        self.assertEqual([10, 11, 12, 13, 14, 15, 16], res[1])


class TestComplexSchemaChanges(unittest.TestCase):
    def test_doesnt_crash(self):
        CSV_INPUT = io.StringIO(
            'name,id,dob,gender,children\n'
            'KÉVIN,kev007,1963-12-13,M,1\n'
            '"JOHN HOWARD, ESQ.",stv534,1992-02-29,M,16\n'
            'JULIA,alp423,0123-01-12,F,0\n'
            )
        SCHEMA_DICT = dict(
            version=1,
            hash=dict(
                type='double hash',
                config=dict(
                    kdf=dict(
                        type='HKDF',
                        hash='SHA256',
                        salt='SCbL2zHNnmsckfzchsNkZY9XoHk96P/G5nUBrM7ybymlEFsMV6PAeDZCNp3rfNUPCtLDMOGQHG4pCQpfhiHCyA==',
                        info='c2NoZW1hX2V4YW1wbGU',
                        keySize=64))),
            features=[
                dict(
                    identifier='name',
                    format=dict(
                        type='string',
                        encoding='utf-8',
                        case='upper'),
                    hashing=dict(
                        ngram=2,
                        weight=2)),
                dict(
                    identifier='id',
                    format=dict(
                        type='string',
                        encoding='ascii',
                        pattern=r'[a-z][a-z][a-z]\d\d\d'),
                    hashing=dict(
                        ngram=1,
                        positional=True)),
                dict(
                    identifier='dob',
                    format=dict(
                        type='date',
                        format='rfc3339',
                        description='When were ya born, m8?'),
                    hashing=dict(
                        ngram=2,
                        positional=True,
                        weight=.5)),
                dict(
                    identifier='gender',
                    format=dict(
                        type='enum',
                        values=['M', 'F']),
                    hashing=dict(
                        ngram=1,
                        positional=False)),
                dict(
                    identifier='children',
                    format=dict(
                        type='integer',
                        maximum=20),
                    hashing=dict(
                        ngram=1,
                        positional=True))])
        KEYS = ('chicken', 'nuggets')

        loaded_schema = schema.Schema.from_json_dict(SCHEMA_DICT)

        results = clk.generate_clk_from_csv(
            CSV_INPUT,
            KEYS,
            loaded_schema,
            validate=True,
            header=True,
            progress_bar=False)
