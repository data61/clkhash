
import unittest
import os
from clkhash import schema


class TestSchemaLoading(unittest.TestCase):

    def test_loading_default_yaml_schema(self):
        fn = os.path.join(
            os.path.dirname(__file__),
            'testdata/default-schema.yaml'
        )

        with open(fn) as schema_file:
            res = schema.load_schema(schema_file)

        self.assertGreater(len(res), 0)
        self.assertIn('identifier', res[0])

    def test_loading_weighted_json_schema(self):
        fn = os.path.join(
            os.path.dirname(__file__),
            'testdata/weighted-schema.json'
        )

        with open(fn) as schema_file:
            res = schema.load_schema(schema_file)

        self.assertEqual(len(res), 2)

        self.assertEqual(res[0]['weight'], 10)
        self.assertEqual(res[1]['weight'], 0)


class TestSchema(unittest.TestCase):

    def test_loading_default_yaml_schema(self):
        fn = os.path.join(
            os.path.dirname(__file__),
            'testdata/default-schema.yaml'
        )

        with open(fn) as schema_file:
            res = schema.load_schema(schema_file)
            schema_identifier_types = schema.get_schema_types(res)
        self.assertGreater(len(schema_identifier_types), 2)



    def test_loading_weighted_json_schema(self):
        fn = os.path.join(
            os.path.dirname(__file__),
            'testdata/weighted-schema.json'
        )

        with open(fn) as schema_file:
            res = schema.load_schema(schema_file)
        schema_identifier_types = schema.get_schema_types(res)

        self.assertEqual(schema_identifier_types[0].weight, 10)
        self.assertEqual(schema_identifier_types[1].weight, 0)

