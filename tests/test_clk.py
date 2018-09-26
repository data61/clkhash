# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

import io
import textwrap
import unittest

from clkhash import clk, schema, randomnames, validate_data
from future.builtins import range


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
    CSV_INPUT = textwrap.dedent("""\
        name,id,dob,gender,children
        KÉVIN,kev007,1963-12-13,M,1
        "JOHN HOWARD, ESQ.",stv534,1992-02-29,M,16
        JULIA,alp423,0123-01-12,F,0
        """)

    SCHEMA_DICT = dict(
        version=1,
        clkConfig=dict(
            l=1024,
            k=30,
            kdf=dict(
                type='HKDF',
                hash='SHA256',
                salt='SCbL2zHNnmsckfzchsNkZY9XoHk96P/G5nUBrM7ybymlEFsMV6PAeDZCNp3rfNUPCtLDMOGQHG4pCQpfhiHCyA==',
                info='c2NoZW1hX2V4YW1wbGU=',
                keySize=64),
            hash=dict(
                type='doubleHash')),
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
                    format='%Y-%m-%d',
                    description='When were ya born?'),
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

    def test_expected_number_of_encodings_returned(self):
        loaded_schema = schema.from_json_dict(self.SCHEMA_DICT)

        results = clk.generate_clk_from_csv(
            io.StringIO(self.CSV_INPUT),
            self.KEYS,
            loaded_schema,
            validate=True,
            header=True,
            progress_bar=False)

        assert len(results) == 3

    def test_encoding_regression(self):
        loaded_schema = schema.from_json_dict(self.SCHEMA_DICT)

        results = clk.generate_clk_from_csv(
            io.StringIO(self.CSV_INPUT),
            self.KEYS,
            loaded_schema,
            validate=True,
            header=True,
            progress_bar=False)

        assert results[0] == 'THHkzVWFYtzMJzmWobTLN8k8VwRN8+na10bN3N9I9oDPGuRZLGpV/QXZYtRZ6/wc+K3W9wvmDA2KpHmOTlVAY9jDblysQ9zlR86OMSbBn+uG3Qxi8EDpUN6nSI5FfOK1Zt77J0ye8P3wifF6QdkFfm3UXNGWil7CPNnUa/fHG0w='
        assert results[1] == '/r76/u//7+1O/3bG//7N5t3evpe/Wt7+v/f/Xt/+9rpXW//f/p7/v//3/vv7v/7/fv7X//vf3Vf/9vP//nd/3t93dt7/dPr/fj7f1z5B3/7W1u/qr+b3//q6729n6/au7772TPz+2s3u/n/88/9OTG/PxvrOh/7Hb89cz+Z3vmo='


class TestHeaderChecking(unittest.TestCase):
    def setUp(self):
        self.schema = randomnames.NameList.SCHEMA
        self.csv_correct_header = (
            'INDEX,NAME freetext,DOB YYYY/MM/DD,GENDER M or F\n'
            '0,Jane Austen,1775/12/16,F\n'
            '1,Bob Hawke,1929/12/09,M\n'
            '2,Tivadar Kanizsa,1933/04/04,M')
        self.csv_incorrect_header_name = (
            'INDEX,THIS IS INCORRECT,DOB YYYY/MM/DD,GENDER M or F\n'
            '0,Jane Austen,1775/12/16,F\n'
            '1,Bob Hawke,1929/12/09,M\n'
            '2,Tivadar Kanizsa,1933/04/04,M')
        self.csv_incorrect_count = (
            'INDEX,THIS IS INCORRECT,DOB YYYY/MM/DD\n'
            '0,Jane Austen,1775/12/16,F\n'
            '1,Bob Hawke,1929/12/09,M\n'
            '2,Tivadar Kanizsa,1933/04/04,M')
        self.csv_no_header = (
            '0,Jane Austen,1775/12/16,F\n'
            '1,Bob Hawke,1929/12/09,M\n'
            '2,Tivadar Kanizsa,1933/04/04,M')

    def test_header(self):
        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_correct_header),
            ('open', 'sesame'),
            self.schema,
            header=True,
            progress_bar=False)
        self.assertEqual(len(out), 3)

        with self.assertRaises(validate_data.FormatError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_incorrect_header_name),
                ('open', 'sesame'),
                self.schema,
                header=True,
                progress_bar=False)

        with self.assertRaises(validate_data.FormatError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_incorrect_count),
                ('open', 'sesame'),
                self.schema,
                header=True,
                progress_bar=False)

        with self.assertRaises(validate_data.FormatError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_no_header),
                ('open', 'sesame'),
                self.schema,
                header=True,
                progress_bar=False)

    def test_ignore_header(self):
        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_correct_header),
            ('open', 'sesame'),
            self.schema,
            header='ignore',
            progress_bar=False)
        self.assertEqual(len(out), 3)

        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_incorrect_header_name),
            ('open', 'sesame'),
            self.schema,
            header='ignore',
            progress_bar=False)
        self.assertEqual(len(out), 3)

        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_incorrect_count),
            ('open', 'sesame'),
            self.schema,
            header='ignore',
            progress_bar=False)
        self.assertEqual(len(out), 3)

        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_no_header),
            ('open', 'sesame'),
            self.schema,
            header='ignore',
            progress_bar=False)
        self.assertEqual(len(out), 2)

    def test_no_header(self):
        with self.assertRaises(validate_data.EntryError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_correct_header),
                ('open', 'sesame'),
                self.schema,
                header=False,
                progress_bar=False)

        with self.assertRaises(validate_data.EntryError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_incorrect_header_name),
                ('open', 'sesame'),
                self.schema,
                header=False,
                progress_bar=False)

        with self.assertRaises(validate_data.FormatError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_incorrect_count),
                ('open', 'sesame'),
                self.schema,
                header=False,
                progress_bar=False)

        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_no_header),
            ('open', 'sesame'),
            self.schema,
            header=False,
            progress_bar=False)
        self.assertEqual(len(out), 3)
