# -*- coding: utf-8 -*-

""" Schema loading and validation.
"""

from __future__ import unicode_literals

import base64
import json
import pkgutil
from typing import Any, Dict, Hashable, Optional, Sequence, Text, TextIO

import jsonschema
from future.builtins import map

from clkhash.backports import raise_from
from clkhash.field_formats import FieldSpec, spec_v1_from_json_dict, spec_v2_from_json_dict
from clkhash.key_derivation import DEFAULT_KEY_SIZE as DEFAULT_KDF_KEY_SIZE


class SchemaError(Exception):
    """ The user-defined schema is invalid.
    """


class MasterSchemaError(Exception):
    """ Master schema missing? Corrupted? Otherwise surprising? This is
        the exception for you!
    """

class Schema:
    
    MASTER_SCHEMA_FILE_NAMES = {1: 'v1.json', 2: 'v2.json'}  # type: Dict[Hashable, Text]

    def __init__(self,
                 version,  # type: int
                 fields,  # type: Sequence[FieldSpec]
                 l,  # type: int
                 hash_type,  # type: str
                 hash_prevent_singularity=None,  # type: Optional[bool]
                 xor_folds=0,  # type: int
                 kdf_type='HKDF',  # type: str
                 kdf_hash='SHA256',  # type: str
                 kdf_info=None,  # type: Optional[bytes]
                 kdf_salt=None,  # type: Optional[bytes]
                 kdf_key_size=DEFAULT_KDF_KEY_SIZE  # type: int
                 ):
        # type: (...) -> Schema
        """ Create a Schema with fields used in v1 & v2 set.

            :param version: the schema version
            :param fields: the features or field definitions
            :param l: The length of the resulting hash in bits. This is the
                length after XOR folding.
            :param hash_type: The hashing function to use. Choices are
                'doubleHash' and 'blakeHash'.
            :param hash_prevent_singularity: Ignored unless hash_type is
                'doubleHash'. Prevents bloom filter collisions in certain
                cases when True.
            :param xor_folds: The number of XOR folds to perform on the hash.
            :param kdf_type: The key derivation function to use. Currently,
                the only permitted value is 'HKDF'.
            :param kdf_hash: The hash function to use in key derivation. The
                options are 'SHA256' and 'SHA512'.
            :param kdf_info: The info for key derivation. See documentation
                of :ref:`hkdf` for details.
            :param kdf_salt: The salt for key derivation. See documentation
                of :ref:`hkdf` for details.
            :param kdf_key_size: The size of the derived keys in bytes.
        """
        self.version = version
        self.fields = fields
        self.l = l
        self.hash_type = hash_type
        self.kdf_type = kdf_type
        self.hash_prevent_singularity = (
            False
            if hash_prevent_singularity is None and hash_type == 'doubleHash'
            else hash_prevent_singularity)
        self.xor_folds = xor_folds
        self.kdf_type = kdf_type
        self.kdf_hash = kdf_hash
        self.kdf_info = kdf_info
        self.kdf_salt = kdf_salt
        self.kdf_key_size = kdf_key_size


    def __repr__(self):
        return "<Schema (v{}): {} fields>".format(self.version, len(self.fields))


    @staticmethod
    def schema_v1(fields,  # type: Sequence[FieldSpec]
                 l,  # type: int
                 k,  # type: int
                 hash_type,  # type: str
                 hash_prevent_singularity=None,  # type: Optional[bool]
                 xor_folds=0,  # type: int
                 kdf_type='HKDF',  # type: str
                 kdf_hash='SHA256',  # type: str
                 kdf_info=None,  # type: Optional[bytes]
                 kdf_salt=None,  # type: Optional[bytes]
                 kdf_key_size=DEFAULT_KDF_KEY_SIZE  # type: int
                 ):
        # type: (...) -> Schema
        """ Create a Schema for v1.

            :param fields: the features or field definitions
            :param l: The length of the resulting hash in bits. This is the
                 length after XOR folding.
            :param k: The number of bits of the hash to set per ngram.
            :param hash_type: The hashing function to use. Choices are
                'doubleHash' and 'blakeHash'.
            :param hash_prevent_singularity: Ignored unless hash_type is
                'doubleHash'. Prevents bloom filter collisions in certain
                cases when True.
            :param xor_folds: The number of XOR folds to perform on the hash.
            :param kdf_type: The key derivation function to use. Currently,
                the only permitted value is 'HKDF'.
            :param kdf_hash: The hash function to use in key derivation. The
                options are 'SHA256' and 'SHA512'.
            :param kdf_info: The info for key derivation. See documentation
                of :ref:`hkdf` for details.
            :param kdf_salt: The salt for key derivation. See documentation
                of :ref:`hkdf` for details.
            :param kdf_key_size: The size of the derived keys in bytes.
         """
        x = Schema(1, fields, l, hash_type, hash_prevent_singularity, xor_folds, kdf_type, kdf_hash, kdf_info, kdf_salt, kdf_key_size)
        x.k = k
        return x

    @staticmethod
    def schema_v2(fields,  # type: Sequence[FieldSpec]
                 l,  # type: int
                 hash_type,  # type: str
                 hash_prevent_singularity=None,  # type: Optional[bool]
                 xor_folds=0,  # type: int
                 kdf_type='HKDF',  # type: str
                 kdf_hash='SHA256',  # type: str
                 kdf_info=None,  # type: Optional[bytes]
                 kdf_salt=None,  # type: Optional[bytes]
                 kdf_key_size=DEFAULT_KDF_KEY_SIZE  # type: int
                 ):
        # type: (...) -> Schema
        """ Create a Schema for v2.

            :param fields: the features or field definitions
            :param l: The length of the resulting hash in bits. This is the
                length after XOR folding.
            :param hash_type: The hashing function to use. Choices are
                'doubleHash' and 'blakeHash'.
            :param hash_prevent_singularity: Ignored unless hash_type is
                'doubleHash'. Prevents bloom filter collisions in certain
                cases when True.
            :param xor_folds: The number of XOR folds to perform on the hash.
            :param kdf_type: The key derivation function to use. Currently,
                the only permitted value is 'HKDF'.
            :param kdf_hash: The hash function to use in key derivation. The
                options are 'SHA256' and 'SHA512'.
            :param kdf_info: The info for key derivation. See documentation
                of :ref:`hkdf` for details.
            :param kdf_salt: The salt for key derivation. See documentation
                of :ref:`hkdf` for details.
            :param kdf_key_size: The size of the derived keys in bytes.
        """
        return Schema(2, fields, l, hash_type, hash_prevent_singularity, xor_folds, kdf_type, kdf_hash, kdf_info, kdf_salt, kdf_key_size)

    @staticmethod
    def from_json_dict(dict, validate=True):
        # type: (Dict[str, Any], bool) -> Schema
        """ Create a Schema for v1 or v2 according to dict

        :param dict: This dictionary must have a `'features'`
                key specifying the columns of the dataset. It must have
                a `'version'` key containing the master schema version
                that this schema conforms to. It must have a `'hash'`
                key with all the globals.
        :param validate: (default True) Raise an exception if the
                schema does not conform to the master schema.
        :return: the Schema
        """
        if validate:
            # This raises iff the schema is invalid.
            Schema._validate_schema_dict(dict)

        version = dict['version']

        clk_config = dict['clkConfig']
        l = clk_config['l']
        xor_folds = clk_config.get('xor_folds', 0)

        clk_hash = clk_config['hash']
        hash_type = clk_hash['type']
        hash_prevent_singularity = clk_hash.get('prevent_singularity')

        kdf = clk_config['kdf']
        kdf_type = kdf['type']
        kdf_hash = kdf.get('hash', 'SHA256')
        kdf_info_string = kdf.get('info')
        kdf_info = (base64.b64decode(kdf_info_string)
                           if kdf_info_string is not None
                           else None)
        kdf_salt_string = kdf.get('salt')
        kdf_salt = (base64.b64decode(kdf_salt_string)
                           if kdf_salt_string is not None
                           else None)
        kdf_key_size = kdf.get('keySize', DEFAULT_KDF_KEY_SIZE)

        features = dict['features']
        if version == 1:
            k = clk_config['k']
            fields = list(map(spec_v1_from_json_dict, features))
            return Schema.schema_v1(fields, l, k, hash_type, hash_prevent_singularity, xor_folds,
                                    kdf_type, kdf_hash, kdf_info, kdf_salt, kdf_key_size)
        elif version == 2:
            fields = list(map(spec_v2_from_json_dict, features))
            return Schema.schema_v2(fields, l, hash_type, hash_prevent_singularity, xor_folds,
                                    kdf_type, kdf_hash, kdf_info, kdf_salt, kdf_key_size)
        else:
            msg = ('Schema version {} is not supported. '
                   'Consider updating clkhash.').format(version)
            raise_from(SchemaError(msg))

    @staticmethod
    def from_json_file(schema_file, validate=True):
        # type: (TextIO, bool) -> Schema
        """ Load a Schema object from a json file.
            :param schema_file: A JSON file containing the schema.
            :param validate: (default True) Raise an exception if the
                schema does not conform to the master schema.
            :raises SchemaError: When the schema is invalid.
            :return: the Schema
        """
        try:
            schema_dict = json.load(schema_file)
        except ValueError as e:  # In Python 3 we can be more specific
            # with json.decoder.JSONDecodeError,
            # but that doesn't exist in Python 2.
            msg = 'The schema is not a valid JSON file.'
            raise_from(SchemaError(msg), e)

        return Schema.from_json_dict(schema_dict, validate=validate)

    @staticmethod
    def _get_master_schema(version):
        # type: (Hashable) -> bytes
        """ Loads the master schema of given version as bytes.

            :param version: The version of the master schema whose path we
                wish to retrieve.
            :raises SchemaError: When the schema version is unknown. This
                usually means that either (a) clkhash is out of date, or (b)
                the schema version listed is incorrect.
            :return: Bytes of the schema.
        """
        try:
            file_name = Schema.MASTER_SCHEMA_FILE_NAMES[version]
        except (TypeError, KeyError) as e:
            msg = ('Schema version {} is not supported. '
                   'Consider updating clkhash.').format(version)
            raise_from(SchemaError(msg), e)

        try:
            schema_bytes = pkgutil.get_data('clkhash',
                                            'master-schemas/{}'.format(file_name))
        except IOError as e:  # In Python 3 we can be more specific with
            # FileNotFoundError, but that doesn't exist in
            # Python 2.
            msg = ('The master schema could not be found. The schema cannot be '
                   'validated. Please file a bug report.')
            raise_from(MasterSchemaError(msg), e)

        if schema_bytes is None:
            msg = ('The master schema could not be loaded. The schema cannot be '
                   'validated. Please file a bug report.')
            raise MasterSchemaError(msg)

        return schema_bytes


    @staticmethod
    def _validate_schema_dict(schema):
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

        master_schema_bytes = Schema._get_master_schema(version)
        try:
            master_schema = json.loads(master_schema_bytes.decode('utf-8'))
        except ValueError as e:  # In Python 3 we can be more specific with
            # json.decoder.JSONDecodeError, but that
            # doesn't exist in Python 2.
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
