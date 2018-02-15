# -*- coding: utf-8 -*-

""" Schema loading and validation.
"""

import base64
import json
import os
from typing import Any, Dict, Hashable, List, TextIO

from future.utils import raise_from
import jsonschema

from clkhash import field_formats

# These are relative to this file. Using tuples to represent hierarches
# for compatibility (thx Windows for those backslashes).
MASTER_SCHEMA_PATHS = {1: ('master-schemas', 'v1.json')}

MASTER_SCHEMA_DIRECTORY = os.path.dirname(__file__)


class GlobalHashingProperties(object):
    def __init__(self, properties_dict=None):
        if properties_dict is not None:
            self.type = properties_dict['type']
            self.kdf_type = properties_dict['config']['kdf']['type']
            self.kdf_hash = properties_dict['config']['kdf']['hash']
            self.kdf_key_size = properties_dict['config']['kdf']['keySize']

            kdf_salt_b64 = properties_dict['config']['kdf']['salt']
            self.kdf_salt = base64.b64decode(kdf_salt_b64)

            kdf_info_b64 = properties_dict['config']['kdf']['type']
            self.kdf_info = base64.b64decode(kdf_info_b64)

            self.xor_folds = 0  # TODO: This will need to change.
            self.l = 1024  # TODO: This will need to change.
            self.k = 30  # TODO: This will need to change.


class Schema(object):
    __slots__ = ('version', 'hashing_globals', 'fields')

    def __init__(self, schema_dict=None, schema_file=None):
        if schema_dict is not None and schema_file is not None:
            msg = ('The schema can be loaded from a dict or a file but not '
                   'both.')
            raise ValueError(msg)

        if schema_file is not None:
            try:
                schema_dict = json.load(schema_file)
            except json.decoder.JSONDecodeError as e:
                raise_from(
                    SchemaError('The schema is not a valid JSON file.'),
                    e)

        if schema_dict is not None:
            # This raises iff the schema is invalid.
            validate_schema_dict(schema_dict)

            features = schema_dict['features']
            self.fields = list(map(field_formats.get_spec, features))
            self.version = schema_dict['version']
            self.hashing_globals = GlobalHashingProperties(schema_dict['hash'])


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
        return os.path.join(MASTER_SCHEMA_DIRECTORY, *rel_path)


class SchemaError(Exception):
    """ The user-defined schema is invalid.
    """
    pass


class MasterSchemaError(Exception):
    """ Master schema missing? Corrupted? Otherwise surprising? This is
        the exception for you!
    """
    pass


def validate_schema_dict(schema):
    # type: (Dict[str, Any]) -> None
    """ Validate the schema.

        This raises iff either the schema or the master schema are
        invalid. If it's successful, it returns nothing.

        :param schema: The schema to validate, as parsed by `json`.
        :raises SchemaError: When the schema is invalid.
        :raises MasterSchemaError: When the master schema is invalid.
    """
    if not isinstance(schema, dict):
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
