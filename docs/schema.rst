.. _schema:

Linkage Schema
==============

As CLKs are usually used for privacy preserving linkage, it is important that
participating organisations agree on how raw personally identifiable information
is encoded to create the CLKs. The linkage schema allows putting more emphasis on
particular features and provides a basic level of data validation.

We call the configuration of how to create CLKs a *linkage schema*. The
organisations agree on a linkage schema to ensure that their respective CLKs have
been created in the same way.

This aims to be an open standard such that different client implementations could
take the schema and create identical CLKs given the same data (and secret keys).

The linkage schema is a detailed description of exactly how to carry out the
encoding operation, along with any configuration for the low level hashing itself.

The format of the linkage schema is defined in a separate
`JSON Schema <https://json-schema.org/specification.html>`_ specification document -
`schemas/v3.json <https://github.com/data61/clkhash/blob/master/clkhash/schemas/v3.json>`_.

Earlier versions of the linkage schema will continue to work, internally they
are converted to the latest version (currently ``v3``).


Basic Structure
---------------

A linkage schema consists of three parts:

* :ref:`version <schema/version>`, contains the version number of the hashing schema.
* :ref:`clkConfig <schema/clkConfig>`, CLK wide configuration, independent of features.
* :ref:`features <schema/features>`, an array of configuration specific to individual features.


Example Schema
--------------

::

    {
      "version": 3,
      "clkConfig": {
        "l": 1024,
        "kdf": {
          "type": "HKDF",
          "hash": "SHA256",
          "salt": "SCbL2zHNnmsckfzchsNkZY9XoHk96P/G5nUBrM7ybymlEFsMV6PAeDZCNp3rfNUPCtLDMOGQHG4pCQpfhiHCyA==",
          "info": "",
          "keySize": 64
        }
      },
      "features": [
        {
          "identifier": "INDEX",
          "ignored": true
        },
        {
          "identifier": "NAME freetext",
          "format": {
            "type": "string",
            "encoding": "utf-8",
            "case": "mixed",
            "minLength": 3
          },
          "hashing": {
            "comparison": {
              "type": "ngram",
              "n": 2
            },
            "strategy": {
                "bitsPerFeature": 100
            },
            "hash": {"type": "doubleHash"}
          }
        },
        {
          "identifier": "DOB YYYY/MM/DD",
          "format": {
            "type": "date",
            "description": "Numbers separated by slashes, in the year, month, day order",
            "format": "%Y/%m/%d"
          },
          "hashing": {
            "comparison": {
              "type": "ngram",
              "n": 1,
              "positional": true
            },
            "strategy": {
              "bitsPerFeature": 200
            },
            "hash": {"type": "doubleHash"}
          }
        },
        {
          "identifier": "GENDER M or F",
          "format": {
            "type": "enum",
            "values": ["M", "F"]
          },
          "hashing": {
            "comparison": {
              "type": "ngram",
              "n": 1
            },
            "strategy": {
              "bitsPerFeature": 400
            },
            "hash": {"type": "doubleHash"}
          }
        }
      ]
    }


A more advanced example can be found `here <_static/example_schema.json>`_.


Schema Components
-----------------

.. _schema/version:

Version
~~~~~~~
Integer value which describes the version of the hashing schema.


.. _schema/clkConfig:

clkConfig
~~~~~~~~~

Describes the general construction of the CLK.

======== ==================  ======== ===========
name     type                optional description
======== ==================  ======== ===========
l        integer             no       the length of the CLK in bits
kdf      :ref:`schema/KDF`   no       defines the key derivation function used to generate individual secrets for each feature derived from the master secret
xorFolds integer             yes      number of XOR folds (as proposed in [Schnell2016]_).
======== ==================  ======== ===========


.. _schema/KDF:

KDF
^^^
We currently only support HKDF (for a basic description, see https://en.wikipedia.org/wiki/HKDF).

======== ======= ======== ===========
name     type    optional description
======== ======= ======== ===========
type     string  no       must be set to "HKDF"
hash     enum    yes      hash function used by HKDF, either "SHA256" or "SHA512"
salt     string  yes      base64 encoded bytes
info     string  yes      base64 encoded bytes
keySize  integer yes      size of the generated keys in bytes
======== ======= ======== ===========


.. _schema/features:

features
~~~~~~~~
A feature is either described by a :ref:`schema/featureConfig`, or alternatively, it can be ignored by the clkhash
library by defining a :ref:`schema/ignoreFeature` section.


.. _schema/ignoreFeature:

ignoreFeature
~~~~~~~~~~~~~
If defined, then clkhash will ignore this feature.

=========== =====================  ======== ===========
name        type                   optional description
=========== =====================  ======== ===========
identifier  string                 no       the name of the feature
ignored     boolean                no       has to be set to "True"
description string                 yes      free text, ignored by clkhash
=========== =====================  ======== ===========


.. _schema/featureConfig:

featureConfig
~~~~~~~~~~~~~

Each feature is configured by:

* identifier, the human readable name. E.g. ``"First Name"``.
* description, a human readable description of this feature.
* format, describes the expected format of the values of this feature
* :ref:`hashing <schema/hashing>`, configures the hashing

=========== =====================  ======== ===========
name        type                   optional description
=========== =====================  ======== ===========
identifier  string                 no       the name of the feature
description string                 yes      free text, ignored by clkhash
hashing     :ref:`schema/hashing`  no       configures feature specific hashing parameters
format      one of:                no       describes the expected format of the feature values
            :ref:`schema/tfo`,
            :ref:`schema/tpfo`,
            :ref:`schema/nfo`,
            :ref:`schema/dfo`,
            :ref:`schema/efo`
=========== =====================  ======== ===========


.. _schema/hashing:

hashingConfig
^^^^^^^^^^^^^

============  ==================================== ======== ===========
name          type                                 optional description
============  ==================================== ======== ===========
comparison    one of:                              no       specifies the comparison technique for this feature.
              :ref:`schema/ngramComparison`,
              :ref:`schema/exactComparison`,
              :ref:`schema/numericComparison`
strategy      one of:                              no       the strategy for assigning bits to the encoding.
              :ref:`schema/bitsPerTokenStrategy`,
              :ref:`schema/bitsPerFeatureStrategy`
hash          one of:                              yes      specifies the hash function for inserting bits into the Bloom filter, defaults to bake hash
              :ref:`schema/doubleHash`
              :ref:`schema/blakeHash`
missingValue  :ref:`schema/missingV`               yes      allows to define how missing values are handled
============  ==================================== ======== ===========

Strategies
^^^^^^^^^^
A strategy defines how often a token is inserted into the Bloom filter.

.. _schema/bitsPerTokenStrategy:

BitsPerTokenStrategy
^^^^^^^^^^^^^^^^^^^^
Insert every token ``bitsPerToken`` number of times.

==============  ======================   ======== ===========
name            type                     optional description
==============  ======================   ======== ===========
bitsPerToken    integer                  no       max number of indices per token
==============  ======================   ======== ===========

.. _schema/bitsPerFeatureStrategy:

BitsPerFeatureStrategy
^^^^^^^^^^^^^^^^^^^^^^
Same number of insertions for each value of this feature, irrespective of the actual number of tokens.
The number of filter insertions for a token is computed by dividing ``bitsPerFeature`` equally amongst
the tokens.

==============  ======================   ======== ===========
name            type                     optional description
==============  ======================   ======== ===========
bitsPerFeature  integer                  no       max number of indices per feature
==============  ======================   ======== ===========

.. _schema/Hash:

Hash
^^^^
Describes and configures the hash that is used to encode the n-grams.

Choose one of:

.. _schema/doubleHash:

DoubleHash
^^^^^^^^^^

as described in [Schnell2011]_.

=================== ======= ======== ===========
name                type    optional description
=================== ======= ======== ===========
type                string  no       must be set to "doubleHash"
prevent_singularity boolean yes      see discussion in https://github.com/data61/clkhash/issues/33
=================== ======= ======== ===========


.. _schema/blakeHash:

BlakeHash
^^^^^^^^^

the (default) option

=================== ======= ======== ===========
name                type    optional description
=================== ======= ======== ===========
type                string  no       must be set to "blakeHash"
=================== ======= ======== ===========


.. _schema/missingV:

missingValue
^^^^^^^^^^^^^^

Data sets are not always complete -- they can contain missing values.
If specified, then clkhash will not check the format for these missing values, and will optionally replace the ``sentinel`` with the
``replaceWith`` value.

===========  =====================   ======== ===========
name         type                    optional description
===========  =====================   ======== ===========
sentinel     string                  no       the sentinel value indicates missing data, e.g. 'Null', 'N/A', '', ...
replaceWith  string                  yes      specifies the value clkhash should use instead of the sentinel value.
===========  =====================   ======== ===========


.. _schema/ngramComparison:

n-gram comparison
^^^^^^^^^^^^^^^^^

Approximate string matching with n-gram tokenization. Also see the `API docs for NgramComparison <clkhash.html#clkhash.comparators.NgramComparison>`_

===========  =====================   ======== ===========
name         type                    optional description
===========  =====================   ======== ===========
type         string                  no       has to be 'ngram'
n            integer                 no       The 'n' in n-gram
positional   boolean                 yes      positional n-grams also contains the position of the n-gram within the string
===========  =====================   ======== ===========


.. _schema/exactComparison:

exact comparison
^^^^^^^^^^^^^^^^

Exact string matching. Also see the `API docs for ExactComparison <clkhash.html#clkhash.comparators.ExactComparison>`_

===========  =====================   ======== ===========
name         type                    optional description
===========  =====================   ======== ===========
type         string                  no       has to be 'exact'
===========  =====================   ======== ===========


.. _schema/numericComparison:

numeric comparison
^^^^^^^^^^^^^^^^^^

Numerical comparisons of integers or floating point numbers such that the distance between two numbers relate to the similarity of the produced tokens. Also see the `API docs for NumericComparison <clkhash.html#clkhash.comparators.NumericComparison>`_

===========          =====================   ======== ===========
name                 type                    optional description
===========          =====================   ======== ===========
threshold_distance   number                  no       positive number, if distance is not more than this, two values will produce overlapping tokens
resolution           integer                 no       produce 2 * resolution + 1 tokens
fractional_precision integer                 yes      quantisation of floats
===========          =====================   ======== ===========

.. _schema/tfo:

textFormat
^^^^^^^^^^^^^

=========== =====================  ======== ===========
name        type                   optional description
=========== =====================  ======== ===========
type        string                 no       has to be "string"
encoding    enum                   yes      one of "ascii", "utf-8", "utf-16", "utf-32". Default is "utf-8".
case        enum                   yes      one of "upper", "lower", "mixed".
minLength   integer                yes      positive integer describing the minimum length of the input string.
maxLength   integer                yes      positive integer describing the maximum length of the input string.
description string                 yes      free text, ignored by clkhash.
=========== =====================  ======== ===========


.. _schema/tpfo:

textPatternFormat
^^^^^^^^^^^^^^^^^

=========== =====================  ======== ===========
name        type                   optional description
=========== =====================  ======== ===========
type        string                 no       has to be "string"
encoding    enum                   yes      one of "ascii", "utf-8", "utf-16", "utf-32". Default is "utf-8".
pattern     string                 no       a regular expression describing the input format.
description string                 yes      free text, ignored by clkhash.
=========== =====================  ======== ===========


.. _schema/nfo:

numberFormat
^^^^^^^^^^^^^

=========== =====================  ======== ===========
name        type                   optional description
=========== =====================  ======== ===========
type        string                 no       has to be "integer"
minimum     integer                yes      integer describing the lower bound of the input values.
maximum     integer                yes      integer describing the upper bound of the input values.
description string                 yes      free text, ignored by clkhash.
=========== =====================  ======== ===========


.. _schema/dfo:

dateFormat
^^^^^^^^^^^^^
A date is described by an ISO C89 compatible strftime() format string. For example, the format string for the internet
date format as described in rfc3339, would be '%Y-%m-%d'.
The clkhash library will convert the given date to the '%Y%m%d' representation for hashing, as any fill character like
'-' or '/' do not add to the uniqueness of an entity.

=========== =====================  ======== ===========
name        type                   optional description
=========== =====================  ======== ===========
type        string                 no       has to be "date"
format      string                 no       ISO C89 compatible format string, eg: for 1989-11-09 the format is '%Y-%m-%d'
description string                 yes      free text, ignored by clkhash.
=========== =====================  ======== ===========

The following subset contains the most useful format codes:

========= ======================================== ==================
directive meaning                                  example
========= ======================================== ==================
%Y        Year with century as a decimal number    1984, 3210, 0001
%y        Year without century, zero-padded        00, 09, 99
%m        Month as a zero-padded decimal number    01, 12
%d        Day of the month, zero-padded            01, 25, 31
========= ======================================== ==================


.. _schema/efo:

enumFormat
^^^^^^^^^^^^^

=========== =====================  ======== ===========
name        type                   optional description
=========== =====================  ======== ===========
type        string                 no       has to be "enum"
values      array                  no       an array of items of type "string"
description string                 yes      free text, ignored by clkhash.
=========== =====================  ======== ===========
