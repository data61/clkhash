## 0.10.0

* Introduced a more secure variant of the double hash encoding scheme.
* Introduced a Blake2 based encoding scheme. Still working on documentation.
* Concurrent hashing now works on Windows as well as linux. This has also been backported to Python 2.
* Command line tool now outputs basic statistics while hashing.
* Command line tool is now officially supported on windows.

We now build clkhash with continuous integration tools that anyone 
can access [Travis CI](https://travis-ci.org/n1analytics/clkhash/) 
and [AppVeyor](https://ci.appveyor.com/project/hardbyte/clkhash).


## 0.9.0

* Adds the option to perform XOR folding. Schnell (2016) claims that it improves privacy whilst having little effect on accuracy; see [*XOR-Folding for hardening Bloom Filter based Encryptions for PPRL*](http://soz-159.uni-duisburg.de/wp-content/uploads/2017/07/XOR-Folding-for-Bloom.pdf) for details.
* Supports online documentation at http://clkhash.readthedocs.io/.
* Fixes minor inconsistency between the treatment of base64 string in Python 2 and Python 3.
* Permits changing of fields' weight in the hash. For example, if the `surname` field has a weight of 2 and the `first name` field has a weight of 1, then the similarity score between two hashes is twice as dependent on the surname. We do this by permitting the surname to set twice as many bits in the hash.

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
