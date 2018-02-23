import os
import unittest

from clkhash import schema

TEST_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), 'testdata')


def test_data_file_path(file_name):
    return os.path.join(TEST_DATA_DIRECTORY, file_name)


class TestSchema(unittest.TestCase):
    def test_schema_validation(self):
        # This is a perfectly fine schema.
        with open(test_data_file_path('good-schema-v1.json')) as f:
            schema.schema_from_json_file(f)

        # This schema is not valid (missing encoding in its feature).
        with open(test_data_file_path('bad-schema-v1.json')) as f:
            with self.assertRaises(schema.SchemaError):
                schema.schema_from_json_file(f)

        # This schema has an unsupported version.
        with open(test_data_file_path(
                'good-but-unsupported-schema-v1.json')) as f:
            with self.assertRaises(schema.SchemaError):
                schema.schema_from_json_file(f)
