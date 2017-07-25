
import os
from clkhash.identifier_types import identifier_type_from_description


def load_schema(schema_file):
    if schema_file is None:
        #log("Assuming default schema")
        schema = [
            {"identifier": 'INDEX'},
            {"identifier": 'NAME freetext'},
            {"identifier": 'DOB YYYY/MM/DD'},
            {"identifier": 'GENDER M or F'}
        ]
    else:
        filename, extension = os.path.splitext(schema_file.name)
        #log("Loading schema from {} file".format(extension))

        if extension == '.json':
            import json
            schema = json.load(schema_file)
        elif extension == '.yaml':
            import yaml
            schema = yaml.load(schema_file)
        else:
            schema_line = schema_file.read().strip()
            schema = [{"identifier": s.strip()} for s in schema_line.split(",")]
        #log("{}".format(schema))

    return schema

def get_schema_types(schema):
    schema_types = [identifier_type_from_description(column) for column in schema]
    return schema_types

