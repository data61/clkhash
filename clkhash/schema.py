import json

import jsonschema

PARENT_SCHEMA_PATH = 'parent_schema.json'
SUPPORTED_VERSIONS = {1}


class UnsupportedSchemaVersionError(Exception):
    pass


def load_schema(schema_file):
    schema = json.load(schema_file)
    with open(PARENT_SCHEMA_PATH) as parent_schema_file:
        parent_schema = json.load(parent_schema_file)

    # Make sure everything is sane.
    # TODO: instead of raising exceptions, print a nice message to the
    #       user. This will involve finding out which situations cause
    #       jsonschema to raise ValidationError and which ones raise
    #       SchemaError.
    jsonschema.validate(schema, parent_schema)
    version = schema['version']
    if version not in SUPPORTED_VERSIONS:
        msg =
        raise UnsupportedSchemaVersionError(
            'Schema version {} is not supported. Consider updating clkhash.'
            .format(version))

    # If we've got this far, then the schema is valid.




    raise NotImplementedError('Schema loading not implemented.')
