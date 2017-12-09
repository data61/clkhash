"""
Convert PII to tokens
"""
from typing import Dict, List

from clkhash.tokenizer import unigramlist, bigramlist


class IdentifierType:
    """
    Base class used for all identifier types.

    Required to provide a mapping of schema to hash type
    uni-gram or bi-gram.
    """

    def __init__(self, unigram=False, weight=1, **kwargs):
        """
        :param unigram: Use uni-gram instead of using bi-grams
        :param int weight: How many times to include this identifier.
        Can be set to zero to skip
        """
        self.weight = int(weight)
        self.tokenizer = unigramlist if unigram else bigramlist
        self.kwargs = kwargs

    def __call__(self, entry):
        # type: (str) -> List[str]
        result = []
        for i in range(self.weight):
            for token in self.tokenizer(entry, **self.kwargs):
                result.append(token)

        return result

basic_types = {
    'INDEX': IdentifierType(weight=0),

    'GENDER M or F': IdentifierType(unigram=True),
    'GENDER freetext': IdentifierType(),

    'DOB YYYY/MM/DD': IdentifierType(toremove='/'),
    'DOB YYYY': IdentifierType(unigram=True, toremove='/'),

    'NAME freetext': IdentifierType(),

    'ANY freetext': IdentifierType(),

    'PHONE freetext': IdentifierType(unigram=True, toremove='()-')
}

# Weighted Types
# Zip Code, Birth Year, Birth Month, Birth Day, Sex, and House number
# can be regarding as identifiers with low error rates and First name,
# last name, street name, place name are in most applications found to
# be more error prone.


weighted_types = {
    'INDEX': IdentifierType(weight=0),

    # gender weight = 1 due to lower identifier entropy
    'GENDER M or F': IdentifierType(unigram=True),

    'DOB DD': IdentifierType(unigram=True, weight=2),
    'DOB MM': IdentifierType(unigram=True, weight=2),
    'DOB YYYY': IdentifierType(unigram=True, toremove='/', weight=2, positional=True),

    'ADDRESS House Number': IdentifierType(weight=2),
    'ADDRESS POSTCODE': IdentifierType(unigram=True, weight=2, positional=True),
    'ADDRESS Place Name': IdentifierType(weight=1),

    'NAME First Name': IdentifierType(),
    'NAME Surname': IdentifierType(),

    'PHONE freetext': IdentifierType(unigram=True, toremove='()-')
}


def identifier_type_from_description(schema_object):
    # type: (Dict[str, str]) -> IdentifierType
    """
    Convert a dictionary describing a feature into an IdentifierType

    :param schema_object:
    :return: An IdentifierType
    """
    assert "identifier" in schema_object
    id = schema_object['identifier']

    if id in basic_types:
        id_type = basic_types[id]
    elif id in weighted_types:
        id_type = weighted_types[id]
    else:
        id_type = IdentifierType(
            weight=schema_object.get('weight', 1)
        )

    # check if there was a custom weight
    if 'weight' in schema_object:
        id_type.weight = schema_object['weight']

    return id_type
