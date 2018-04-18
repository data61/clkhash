from clkhash.schema import Schema
from clkhash.clk import generate_clks


def test_missing_value_integration():
    # we create two clks, one from PII which contains the 'replaceWith' values, one which contains the sentinels.
    # if everything goes right, then the two clks will be identical.
    schema_dict = dict(version=1,
        clkConfig=dict(l=1024, k=20, hash=dict(type='doubleHash'), kdf=dict(type='HKDF')),
        features=[
            dict(identifier='name',
                 format=dict(type='string', encoding='utf-8'),
                 hashing=dict(ngram=2, missingValue=dict(sentinel='null', replaceWith='Bob'))),
            dict(identifier='age',
                 format=dict(type='integer'),
                 hashing=dict(ngram=1, missingValue=dict(sentinel='NA', replaceWith='42')))
        ])
    schema = Schema.from_json_dict(schema_dict)

    pii = [['Bob', '42'], ['null', 'NA']]

    clks = generate_clks(pii, schema=schema, keys=('sec1', 'sec2'), validate=True, callback=None)
    assert len(clks) == 2
    assert clks[0] == clks[1]