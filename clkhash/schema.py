import json

from future.utils import raise_from
import jsonschema

MASTER_SCHEMA_PATHS = {1: 'master-schema-v1.json'}


class SchemaError(Exception):
    pass


class MasterSchemaError(Exception):
    pass


def validate_schema(schema):
    if type(schema) is not dict:
        raise SchemaError('The top level of the schema file is a {}, '
                          'whereas a dict is expected.'
                          .format(type(schema).__name__))

    if 'version' in schema:
        version = schema['version']
    else:
        raise SchemaError('A format version is expected in the schema.')

    if version in MASTER_SCHEMA_PATHS:
        master_schema_path = MASTER_SCHEMA_PATHS[version]
    else:
        raise SchemaError(
            'Schema version {} is not supported. Consider updating clkhash.'
            .format(version))

    try:
        with open(master_schema_path) as master_schema_file:
            master_schema = json.load(master_schema_file)
    except FileNotFoundError as e:
        raise_from(MasterSchemaError('The master schema could not be found. '
                                     'The schema cannot be validated. Please '
                                     'file a bug report.'), e)
    except json.decoder.JSONDecodeError as e:
        raise_from(MasterSchemaError('The master schema is not a valid JSON '
                                     'file. The schema cannot be validated. '
                                     'Please file a bug report.'), e)

    try:
        jsonschema.validate(schema, master_schema)
    except jsonschema.exceptions.ValidationError as e:
        raise_from(SchemaError('The schema is not valid.'), e)
    except jsonschema.exceptions.SchemaError as e:
        raise_from(MasterSchemaError('The master schema is not valid. The '
                                     'schema cannot be validated. Please file '
                                     'a bug report.'), e)


def load_schema(schema_file):
    try:
        schema = json.load(schema_file)
    except json.decoder.JSONDecodeError as e:
        raise_from(SchemaError('The schema is not a valid JSON file.'), e)

    validate_schema(schema)  # This raises iff the schema is invalid.

    raise NotImplementedError('Schema loading not implemented.')
