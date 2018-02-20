# -*- coding: utf-8 -*-

""" Schema loading and validation.
"""

from __future__ import unicode_literals

import base64
import json
import os
from typing import Any, Dict, Hashable, List, Optional, Text, TextIO, Tuple

from future.utils import raise_from
import jsonschema

from clkhash import field_formats

# These are relative to this file. Using tuples to represent hierarches
# for compatibility (thx Windows for those backslashes).
MASTER_SCHEMA_PATHS = {1: ('master-schemas', 'v1.json')}  # type: Dict[Hashable, Tuple[Text, ...]]

MASTER_SCHEMA_DIRECTORY = os.path.dirname(__file__)


class GlobalHashingProperties(object):
    """ Stores global hashing properties.

        :ivar type: TODO: find out what this does.
        :ivar kdf_type: TODO: find out what this does.
        :ivar kdf_hash: TODO: find out what this does.
        :ivar kdf_key_size: TODO: find out what this does.
        :ivar kdf_salt: TODO: find out what this does.
        :ivar kdf_info: TODO: find out what this does.
        :ivar xor_folds: Number of XOR folds to perform.
        :ivar l: Length of the Bloom filter (in bits).
        :ivar k: Number of bits set per n-gram.
    """
    __slots__ = ('type', 'kdf_type', 'kdf_hash', 'kdf_key_size', 'kdf_salt',
                 'kdf_info', 'xor_folds', 'l', 'k')

    def __init__(self, **kwargs):
        # type: (...) -> None
        """ Make a GlobalHashingProperties object from keyword
            arguments.

            :param k: (optional) Value of `self.k`.
            :param kdf_hash: (optional) Value of `self.kdf_hash`.
            :param kdf_info: (optional) Value of `self.kdf_info`.
            :param kdf_key_size: (optional) Value of `self.kdf_key_size`.
            :param kdf_salt: (optional) Value of `self.kdf_salt`.
            :param kdf_type: (optional) Value of `self.kdf_type`.
            :param l: (optional) Value of `self.l`.
            :param type: (optional) Value of `self.type`.
            :param xor_folds: (optional) Value of `self.xor_folds`.
        """
        if 'k' in kwargs:
             self.k = kwargs['k']
        if 'kdf_hash' in kwargs:
            self.kdf_hash = kwargs['kdf_hash']
        if 'kdf_info' in kwargs:
            self.kdf_info = kwargs['kdf_info']
        if 'kdf_key_size' in kwargs:
            self.kdf_key_size = kwargs['kdf_key_size']
        if 'kdf_salt' in kwargs:
            self.kdf_salt = kwargs['kdf_salt']
        if 'kdf_type' in kwargs:
            self.kdf_type = kwargs['kdf_type']
        if 'l' in kwargs:
            self.l = kwargs['l']
        if 'type' in kwargs:
            self.type = kwargs['type']
        if 'xor_folds' in kwargs:
            self.xor_folds = kwargs['xor_folds']

    @classmethod
    def from_json_dict(cls, properties_dict):
        # type: (Dict[str, Any]) -> GlobalHashingProperties
        """ Make a GlobalHashingProperties object from a dictionary.

            The dictionary must have a `'type'` key and a `'config'`
            key. The `'config'` key must map to a dictionary
            containinng a `'kdf'` key, which itself maps to a
            dictioanry. That dictionary must have `'type'`, `'hash'`,
            `'keySize'`, `'salt'`, and `'type'` keys.

            :param properties_dict: The dictionary to use.
        """
        result = cls()

        result.type = properties_dict['type']
        result.kdf_type = properties_dict['config']['kdf']['type']
        result.kdf_hash = properties_dict['config']['kdf']['hash']
        result.kdf_key_size = properties_dict['config']['kdf']['keySize']

        kdf_salt_b64 = properties_dict['config']['kdf']['salt']
        result.kdf_salt = base64.b64decode(kdf_salt_b64)

        kdf_info_b64 = properties_dict['config']['kdf']['type']
        result.kdf_info = base64.b64decode(kdf_info_b64)

        result.xor_folds = 0  # TODO: This will need to change.
        result.l = 1024  # TODO: This will need to change.
        result.k = 30  # TODO: This will need to change.

        return result


class Schema(object):
    """ Overall schema for hashing.

        A single object contains all the settings you will need, want,
        or desire.

        :ivar version: Version for the schema. Needed to keep behaviour
            consistent between Clkhash versions for the same schema.
        :ivar hashing_globals: Hashing globals. Your salts and lengths
            and stuff.
        :ivar fields: The columns in our dataset.
    """
    __slots__ = ('version', 'hashing_globals', 'fields')

    def __init__(self, **kwargs):
        # type: (...) -> None
        """ Make a Schema object from keyword arguments.

            :param version: (optional) Value of `self.version`.
            :param global_properties: (optional) Value of
                `self.global_properties`.
            :param fields: (optional) Value of `self.fields`.
        """
        if 'version' in kwargs:
             self.version = kwargs['version']
        if 'hashing_globals' in kwargs:
            self.hashing_globals = kwargs['hashing_globals']
        if 'fields' in kwargs:
            self.fields = kwargs['fields']

    @classmethod
    def from_json_dict(cls, schema_dict, validate=True):
        # type: (Dict[str, Any], bool) -> Schema
        """ Make a Schema object from a dictionary.

            The dictionary must have a `'features'` key specifying the
            columns of the dataset. It must have a `'version'` key
            containing the master schema version that this schema
            conforms to. It must have a `'hash'` key with all the
            globals.

            :param schema_dict: The dictionary to use.
            :param validate: (default True) Should we throw if the
                schema does not conform to the master schema?
        """
        if validate:
            # This raises iff the schema is invalid.
            validate_schema_dict(schema_dict)

        result = cls()

        features = schema_dict['features']
        result.fields = list(map(field_formats.spec_from_json_dict, features))

        result.version = schema_dict['version']

        result.hashing_globals = GlobalHashingProperties.from_json_dict(
            schema_dict['hash'])

        return result


def get_master_schema_path(version):
    # type: (Hashable) -> Optional[str]
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


class MasterSchemaError(Exception):
    """ Master schema missing? Corrupted? Otherwise surprising? This is
        the exception for you!
    """


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


def schema_from_json_file(schema_file):
    # (TextIO) -> Schema
    """ Load a Schema object from a json file.

        :param schema_file: A JSON file containing the schema.
        :raises SchemaError: When the schema is invalid.
    """
    try:
        schema_dict = json.load(schema_file)
    except json.decoder.JSONDecodeError as e:
        raise_from(
            SchemaError('The schema is not a valid JSON file.'),
            e)

    return Schema.from_json_dict(schema_dict, validate=True)
