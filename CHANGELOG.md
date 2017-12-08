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
