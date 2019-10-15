from clkhash import schema
from clkhash.clk import generate_clks
import json


def test_missing_value_integration():
    # we create two clks, one from PII which contains the 'replaceWith' values, one which contains the sentinels.
    # if everything goes right, then the two clks will be identical.

    schema_json = """
    {
      "version": 2,
      "clkConfig": {
        "l": 1024,
        "kdf": {
          "type": "HKDF"
        }
      },
      "features": [
        {
          "identifier": "name",
          "format": {
            "type": "string",
            "encoding": "utf-8"
          },
          "hashing": {
            "ngram": 2,
            "strategy": {
              "k": 20
            },
            "missingValue": {
              "sentinel": "null",
              "replaceWith": "Bob"
            }
          }
        },
        {
          "identifier": "age",
          "format": {
            "type": "integer"
          },
          "hashing": {
            "ngram": 1,
            "strategy": {
              "k": 20
            },
            "missingValue": {
              "sentinel": "NA",
              "replaceWith": "42"
            }
          }
        }
      ]
    }
    """
    schema_dict = json.loads(schema_json)
    s = schema.from_json_dict(schema_dict)

    pii = [['Bob', '42'], ['null', 'NA']]

    clks = generate_clks(pii, schema=s, key='sec')
    assert len(clks) == 2
    assert clks[0] == clks[1]
