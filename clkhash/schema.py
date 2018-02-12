# -*- coding: utf-8 -*-

""" Schema loading and validation.
"""

import json
from typing import Any, Dict, Hashable, List, TextIO

from future.utils import raise_from
import jsonschema

from clkhash import field_formats

# These are relative to this file.
MASTER_SCHEMA_PATHS = {1: 'master-schema-v1.json'}

MASTER_SCHEMA_DIRECTORY = os.path.dirname(__file__)


def get_master_schema_path(version):
    # type: (Hashable) -> str
    """ Get the path of the master schema given a version.

        :param version: The version of the master schema whose path we
            wish to retrieve.
    """
    try:
        rel_path = MASTER_SCHEMA_PATHS[version]
    except (TypeError, KeyError):
        return None
    else:
        return os.path.join(MASTER_SCHEMA_DIRECTORY, rel_path)


class SchemaError(Exception):
    """ The user-defined schema is invalid.
    """
    pass


class MasterSchemaError(Exception):
    """ Master schema missing? Corrupted? Otherwise surprising? This is
        the exception for you!
    """
    pass


def validate_schema(schema):
    # type: (Dict[str, Any]) -> None
    """ Validate the schema.

        This raises iff either the schema or the master schema are
        invalid. If it's successful, it returns nothing.

        :param schema: The schema to validate, as parsed by `json`.
        :raises SchemaError: When the schema is invalid.
        :raises MasterSchemaError: When the master schema is invalid.
    """
    if type(schema) is not dict:
        msg = ('The top level of the schema file is a {}, whereas a dict is '
               'expected.'.format(type(schema).__name__))
        raise SchemaError(msg)

    if 'version' in schema:
        version = schema['version']
    else:
        raise SchemaError('A format version is expected in the schema.')

    master_schema_path = get_master_schema_path(version)
    if master_schema_path is None:
        raise SchemaError(
            'Schema version {} is not supported. Consider updating clkhash.'
            .format(version))

    try:
        with open(master_schema_path) as master_schema_file:
            master_schema = json.load(master_schema_file)
    except FileNotFoundError as e:
        msg = ('The master schema could not be found. The schema cannot be '
               'validated. Please file a bug report.')
        raise_from(MasterSchemaError(msg), e)
    except json.decoder.JSONDecodeError as e:
        msg = ('The master schema is not a valid JSON file. The schema cannot '
               'be validated. Please file a bug report.')
        raise_from(MasterSchemaError(msg), e)

    try:
        jsonschema.validate(schema, master_schema)
    except jsonschema.exceptions.ValidationError as e:
        raise_from(SchemaError('The schema is not valid.'), e)
    except jsonschema.exceptions.SchemaError as e:
        msg = ('The master schema is not valid. The schema cannot be '
               'validated. Please file a bug report.')
        raise_from(MasterSchemaError(msg), e)


def load_schema(schema_file):
    # type: (TextIO) -> List[field_formats.FieldSpec]
    """ Loads and validates a schema.

        The schema file is loaded as a list of `FieldSpec` objects.

        :param schema_file: The schema file to load.
        :returns: A list of `FieldSpec`s, one for each field.
    """
    try:
        schema = json.load(schema_file)
    except json.decoder.JSONDecodeError as e:
        raise_from(SchemaError('The schema is not a valid JSON file.'), e)

    validate_schema(schema)  # This raises iff the schema is invalid.

    raise NotImplementedError('Schema loading not implemented.')
