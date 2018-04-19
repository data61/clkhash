import unittest

from clkhash.backports import re_compile_full
from clkhash.field_formats import (DateSpec, EnumSpec, FieldHashingProperties,
                                   IntegerSpec, StringSpec)
from clkhash.validate_data import (EntryError, FormatError,
                                   validate_entries, validate_header,
                                   validate_row_lengths)


class FieldsMaker(unittest.TestCase):
    def setUp(self):
        ascii_hashing = FieldHashingProperties(encoding='ascii', ngram=2)
        self.fields = [
            StringSpec(
                identifier='given name',
                case='lower',
                min_length=1,
                max_length=None,
                hashing_properties=ascii_hashing
            ),
            StringSpec(
                identifier='surname',
                case='upper',
                min_length=1,
                max_length=None,
                hashing_properties=ascii_hashing
            ),
            StringSpec(
                identifier='email address',
                regex=r'.+@.+\..+',
                hashing_properties=ascii_hashing
            ),
            IntegerSpec(
                identifier='age',
                minimum=18,
                maximum=99,
                hashing_properties=ascii_hashing
            ),
            DateSpec(
                identifier='join date',
                format='%Y-%m-%d',
                hashing_properties=ascii_hashing
            ),
            EnumSpec(
                identifier='account type',
                values=['free', 'paid'],
                hashing_properties=ascii_hashing
            )
        ]


class TestValidateRowLengths(FieldsMaker):
    def test_good_data(self):
        row = [['john', 'DOE', 'john.doe@generic.com',
                                            '23', '2015-10-21', 'free']]
        validate_row_lengths(self.fields, row)  # This should not throw
    
    def test_missing_data(self):
        row = [['john', 'DOE', 'john.doe@generic.com', '2015-10-21', 'free']]
        #                         missing 'age' field ^
        msg = 'Expected missing entry to throw FormatError.'
        with self.assertRaises(FormatError, msg=msg):
            validate_row_lengths(self.fields, row)


class TestValidateEntries(FieldsMaker):
    def test_good_data(self):
        row = [['john', 'DOE', 'john.doe@generic.com',
                                            '23', '2015-10-21', 'free']]
        validate_entries(self.fields, row)  # This should not throw
    
    def test_invalid_data(self):
        msg = 'Expected invalid entry to throw EntryError.'

        row = [['John', 'DOE', 'john.doe@generic.com',
                                            '23', '2015-10-21', 'free']]
        #        ^ Invalid case.
        with self.assertRaises(EntryError, msg=msg):
            validate_entries(self.fields, row)

        row = [['john', 'doe', 'john.doe@generic.com',
                                            '23', '2015-10-21', 'free']]
        #                ^^^ Invalid case.
        with self.assertRaises(EntryError, msg=msg):
            validate_entries(self.fields, row)


class TestValidateHeader(FieldsMaker):
    def test_good_column_names(self):
        column_names = ['given name', 'surname', 'email address',
                        'age', 'join date', 'account type']
        validate_header(self.fields, column_names)  # This should not throw

    def test_missing_column_names(self):
        column_names = ['given name', 'surname', 'email address',
                        'join date', 'account type']  # missing 'age'
        msg = 'Expected missing column name to throw FormatError.'
        with self.assertRaises(FormatError, msg=msg):
            validate_header(self.fields, column_names)

    def test_invalid_column_names(self):
        column_names = ['given name', 'surname', 'email address',
                        'age', 'join date', 'nonexistent field']
        msg = 'Expected invalid column name to throw FormatError.'
        with self.assertRaises(FormatError, msg=msg):
            validate_header(self.fields, column_names)
