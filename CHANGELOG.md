## 0.9.0

* Adds the option to perform XOR folding. See *XOR-Folding for hardening Bloom Filter based Encryptions for PPRL* by Schnell (2016).
* Supports online documentation at http://clkhash.readthedocs.io/.
* Fixes minor inconsistency between the treatment of base64 string in Python 2 and Python 3.
* Permits changing of fields' weight in the hash.

## 0.8.1

* Adds a simple progress bar for the command line utility.
* Added type checking with MyPy for both Python 2 and 3.

Try run the type checker yourself with:

    pip install mypy
    mypy clkhash --ignore-missing-imports --strict-optional --no-implicit-optional --disallow-untyped-calls

## 0.8.0

Each identifier is hashed using different keys derived with a HKDF.

### Breaking Changes

* The `bloomfilter` api has changed. In `calculate_bloom_filters(dataset, schema, keys)`
  the keys have changed into two lists of keys (from just two keys).

* Added cryptography dependency. Removing support Python 3.3.

### Other Changes

Several improvements to continuous testing with Jenkins - such as adding
in code coverage, posting github status checks.

More e2e testing.

## 0.7.3

Soft launch - First version on pypi.
