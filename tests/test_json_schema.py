import json
import unittest

import os
from jsonschema import validate
from jsonschema.exceptions import ValidationError, SchemaError


class TestJsonSchema(unittest.TestCase):

    def test_example_validation(self):
        with open(os.path.join(os.path.abspath('..'), 'docs/_static/schema.json')) as schema_file, \
                open(os.path.join(os.path.abspath('..'), 'docs/_static/example_schema.json')) as example_file:
            schema = json.load(schema_file)
            example = json.load(example_file)
            try:
                validate(example, schema)
            except ValidationError as ve:
                self.fail('validation failed! Reason: {}'.format(ve))
            except SchemaError as se:
                self.fail('invalid schema! Reason: {}'.format(se))
