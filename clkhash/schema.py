from typing import List, Dict, Optional, TextIO

import os
from clkhash.identifier_types import IdentifierType, identifier_type_from_description


def load_schema(schema_file):
    # type: (Optional[TextIO]) -> List[Dict[str, str]]
    if schema_file is None:
        schema = [
            {"identifier": 'INDEX'},
            {"identifier": 'NAME freetext'},
            {"identifier": 'DOB YYYY/MM/DD'},
            {"identifier": 'GENDER M or F'}
        ]
    else:
        filename, extension = os.path.splitext(schema_file.name)

        if extension == '.json':
            import json
            schema = json.load(schema_file)
        elif extension == '.yaml':
            import yaml
            schema = yaml.load(schema_file)
        else:
            schema_line = schema_file.read().strip()
            schema = [{"identifier": s.strip()} for s in schema_line.split(",")]

    return schema


def get_schema_types(schema):
    # type: (List[Dict[str, str]]) -> List[IdentifierType]
    schema_types = [identifier_type_from_description(column) for column in schema]
    return schema_types

