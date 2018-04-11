.. _schema:

Hashing Schema
==============

.. caution::

   This document and the referenced ``schema.json`` file are still in a draft status.


As CLKs are usually used for privacy preserving linkage, it is important, that participating organisations agree on how
raw personally identifiable information is hashed to create the CLKs.

We call the configuration of how to create CLKs a *hashing schema*. The organisations agree on one hashing schema
as configuration to ensure that the have been created in the same way.

This aims to be an open standard such that different client implementations could take the schema
and create identical CLKS given the same data.

The hashing-schema is a detailed description of exactly what is fed to the hashing operation,
along with any configuration for the hashing itself.

The format of the hashing schema is defined in a separate ``JSON Schema`` document `hashing-schema.json <_static/schema.json>`_.


Basic Structure
---------------

A hashing schema consists of three parts:

* :ref:`version <schema/version>`, contains the version number of the hashing schema
* :ref:`clkConfig <schema/clkConfig>`, CLK wide configuration, independent of features
* :ref:`features <schema/features>`, configuration that is specific to the individual features


Example Schema
--------------

::

    {
      "version": 1,
      "clkConfig": {
        "l": 1024,
        "k": 20,
        "hash": {
          "type": "doubleHash"
        },
        "kdf": {
          "type": "HKDF"
        }
      },
      "features": [
        {
          "identifier": "full name",
          "format": {
            "type": "string",
            "maxLength": 30,
            "encoding": "utf-8"
          },
          "hashing": { "ngram": 2 }
        },
        {
          "identifier": "gender",
          "format": {
            "type": "enum",
            "values": ["M", "F", "O"]
          },
          "hashing": { "ngram": 1 }
        },
        {
          "identifier": "postcode",
          "format": {
            "type": "integer",
            "minimum": 1000,
            "maximum": 9999
          },
          "hashing": { "ngram": 1, "positional": true }
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
k        integer             no       max number of indices per n-gram
xorFolds integer             yes      number of XOR folds (as proposed in [Schnell2016]_).
kdf      :ref:`schema/KDF`   no       defines the key derivation function used to generate individual secrets for each feature derived from the master secret
hash     :ref:`schema/Hash`  no       defines the hashing scheme to encode the n-grams
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


.. _schema/Hash:

Hash
^^^^
Describes and cofigures the hash that is used to encode the n-grams.

Choose one of:

* *double hash*, as described in [Schnell2011]_.

=================== ======= ======== ===========
name                type    optional description
=================== ======= ======== ===========
type                string  no       must be set to "doubleHash"
prevent_singularity boolean yes      see discussion in https://github.com/n1analytics/clkhash/issues/33
=================== ======= ======== ===========

* *blake hash*

=================== ======= ======== ===========
name                type    optional description
=================== ======= ======== ===========
type                string  no       must be set to "blakeHash"
=================== ======= ======== ===========


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
A feature is configured in three parts:

* identifier, the name of the feature
* format, describes the expected format of the values of this feature
* hashing, configures the hashing

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

=========== =====================  ======== ===========
name        type                   optional description
=========== =====================  ======== ===========
ngram       integer                no       specifies the n in n-gram (the tokenization of the input values).
positional  boolean                yes      adds the position to the n-grams. String "222" would be tokenized (as uni-grams) to "1 2", "2 2", "3 2"
weight      float                  yes      positive number, which adjusts the number of hash functions (k) used for encoding. Thus giving this feature more or less importance compared to others.
=========== =====================  ======== ===========


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
minimum     integer                yes      positive integer describing the lower bound of the input values.
maximum     integer                yes      positive integer describing the upper bound of the input values.
description string                 yes      free text, ignored by clkhash.
=========== =====================  ======== ===========


.. _schema/dfo:

dateFormat
^^^^^^^^^^^^^

=========== =====================  ======== ===========
name        type                   optional description
=========== =====================  ======== ===========
type        string                 no       has to be "date"
format      enum                   no       one of ["rfc3339"]. That's the standard internet format: yyyy-mm-dd.
description string                 yes      free text, ignored by clkhash.
=========== =====================  ======== ===========


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

