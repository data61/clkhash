from __future__ import unicode_literals

import io
import os
import unittest

from clkhash import schema

TEST_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), 'testdata')


def _test_data_file_path(file_name):
    return os.path.join(TEST_DATA_DIRECTORY, file_name)


class TestSchemaValidation(unittest.TestCase):
    def test_good_schema(self):
        # These are some perfectly fine schemas.
        with open(_test_data_file_path('good-schema-v1.json')) as f:
            schema.Schema.from_json_file(f)

    def test_invalid_schema(self):
        # This schema is not valid (missing encoding in its feature).
        with open(_test_data_file_path('bad-schema-v1.json')) as f:
            with self.assertRaises(schema.SchemaError):
                schema.Schema.from_json_file(f)

    def test_valid_but_unsupported_schema(self):
        # This schema has an unsupported version.
        with open(_test_data_file_path(
                'good-but-unsupported-schema-v1.json')) as f:
            with self.assertRaises(schema.SchemaError):
                schema.Schema.from_json_file(f)

    def test_invalid_json_schema(self):
        invalid_schema_file = io.StringIO('{')  # Invalid json.
        msg = 'Invalid JSON in schema should raise SchemaError.'
        with self.assertRaises(schema.SchemaError, msg=msg):
            schema.Schema.from_json_file(invalid_schema_file)

    def test_list_schema(self):
        invalid_schema_file = io.StringIO('[]')  # Must be dict instead.
        msg = 'List as top element should raise SchemaError.'
        with self.assertRaises(schema.SchemaError, msg=msg):
            schema.Schema.from_json_file(invalid_schema_file)

    def test_string_schema(self):
        invalid_schema_file = io.StringIO('"foo"')  # Must be dict.
        msg = 'Literal as top element should raise SchemaError.'
        with self.assertRaises(schema.SchemaError, msg=msg):
            schema.Schema.from_json_file(invalid_schema_file)

    def test_no_version(self):
        invalid_schema_file = io.StringIO('{}')  # Missing version.
        msg = 'Schema with no version should raise SchemaError.'
        with self.assertRaises(schema.SchemaError, msg=msg):
            schema.Schema.from_json_file(invalid_schema_file)

    def test_missing_master(self):
        # This shouldn't happen but we need to be able to handle it if,
        # for example, we have a corrupt install.
        original_paths = schema.MASTER_SCHEMA_FILE_NAMES
        schema.MASTER_SCHEMA_FILE_NAMES = {1: 'nonexistent.json'}

        msg = 'Missing master schema should raise MasterSchemaError.'
        with self.assertRaises(schema.MasterSchemaError, msg=msg):
            schema.validate_schema_dict({'version': 1})

        schema.MASTER_SCHEMA_FILE_NAMES = original_paths
