#!/usr/bin/env python3

"""
Generate a Bloom filter
"""

import base64
import hmac
import math
import struct
from enum import Enum
from functools import partial
from hashlib import md5, sha1
from typing import Callable, Iterable, List, Sequence, Text, Tuple

from bitarray import bitarray
from future.builtins import range, zip

from clkhash import tokenizer
from clkhash.backports import int_from_bytes
from clkhash.field_formats import FieldSpec
from clkhash.schema import Schema

try:
    from hashlib import blake2b
except ImportError:
    # We are in Python older than 3.6.
    from pyblake2 import blake2b  # type: ignore
    # Ignore because otherwise Mypy raises errors, thinking that
    # blake2b is already defined.



def double_hash_encode_ngrams(ngrams,    # type: Iterable[str]
                              keys,      # type: Sequence[bytes]
                              ks,        # type: Iterable[int]
                              l,         # type: int
                              encoding   # type: str
                              ):
    # type: (...) -> bitarray
    """ Computes the double hash encoding of the provided ngrams with the given keys.

        Using the method from
        http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

        :param ngrams: list of n-grams to be encoded
        :param keys: hmac secret keys for md5 and sha1 as bytes
        :param ks: number of hash functions to use for each ngram
        :param l: length of the output bitarray
        :param encoding: the encoding to use when turning the ngrams to bytes

        :return: bitarray of length l with the bits set which correspond to the encoding of the ngrams
    """
    key_sha1, key_md5 = keys
    bf = bitarray(l)
    bf.setall(False)

    for m, k in zip(ngrams, ks):
        sha1hm = int(hmac.new(key_sha1, m.encode(encoding=encoding), sha1).hexdigest(), 16) % l
        md5hm = int(hmac.new(key_md5, m.encode(encoding=encoding), md5).hexdigest(), 16) % l
        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = 1
    return bf


def double_hash_encode_ngrams_non_singular(ngrams,  # type: Iterable[str]
                                           keys,  # type: Sequence[bytes]
                                           ks,  # type: Iterable[int]
                                           l,  # type: int
                                           encoding  # type: str
                                           ):
    # type: (...) -> bitarray.bitarray
    """
    computes the double hash encoding of the provided n-grams with the given keys.

    The original construction of [Schnell2011]_ displays an abnormality for certain inputs:
      An n-gram can be encoded into just one bit irrespective of the number of k.

    Their construction goes as follows: the :math:`k` different indices :math:`g_i` of the Bloom filter for an n-gram
    :math:`x` are defined as:

    .. math::
      g_{i}(x) = (h_1(x) + i h_2(x)) \mod l

    with :math:`0 \leq i < k` and :math:`l` is the length of the Bloom filter. If the value of the hash of :math:`x` of
    the second hash function is a multiple of :math:`l`, then

    .. math::
      h_2(x) = 0 \mod l

    and thus

    .. math::
      g_i(x) = h_1(x) \mod l,

    irrespective of the value :math:`i`. A discussion of this potential flaw can be found
    `here <https://github.com/n1analytics/clkhash/issues/33>`_.

    :param ngrams: list of n-grams to be encoded
    :param keys: tuple with (key_sha1, key_md5).
        That is, (hmac secret keys for sha1 as bytes, hmac secret keys for md5 as bytes)
    :param ks: number of hash functions to use for each ngram
    :param l: length of the output bitarray
    :param encoding: the encoding to use when turning the ngrams to bytes

    :return: bitarray of length l with the bits set which correspond to the encoding of the ngrams
    """
    key_sha1, key_md5 = keys
    bf = bitarray(l)
    bf.setall(False)
    for m, k in zip(ngrams, ks):
        m_bytes = m.encode(encoding=encoding)

        sha1hm_bytes = hmac.new(key_sha1, m_bytes, sha1).digest()
        md5hm_bytes = hmac.new(key_md5, m_bytes, md5).digest()

        sha1hm = int_from_bytes(sha1hm_bytes, 'big') % l
        md5hm = int_from_bytes(md5hm_bytes, 'big') % l

        i = 0
        while md5hm == 0:
            md5hm_bytes = hmac.new(
                key_md5, m_bytes + chr(i).encode(), md5).digest()
            md5hm = int_from_bytes(md5hm_bytes, 'big') % l
            i += 1

        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = True
    return bf


def blake_encode_ngrams(ngrams,  # type: Iterable[str]
                        keys,  # type: Sequence[bytes]
                        ks,  # type:  Iterable[int]
                        l,  # type: int
                        encoding  # type: str
                        ):
    # type: (...) -> bitarray.bitarray
    """
    Computes the encoding of the provided ngrams using the BLAKE2 hash function.

    We deliberately do not use the double hashing scheme as proposed in [Schnell2011]_, because this
    would introduce an exploitable structure into the Bloom filter. For more details on the
    weakness, see [Kroll2015]_.

    In short, the double hashing scheme only allows for :math:`l^2` different encodings for any possible n-gram,
    whereas the use of :math:`k` different independent hash functions gives you :math:`\sum_{j=1}^{k}{\\binom{l}{j}}`
    combinations.


    **Our construction**

    It is advantageous to construct Bloom filters using a family of hash functions with the property of
    `k-independence <https://en.wikipedia.org/wiki/K-independent_hashing>`_ to compute the indices for an entry.
    This approach minimises the change of collisions.

    An informal definition of *k-independence* of a family of hash functions is, that if selecting a function at random
    from the family, it guarantees that the hash codes of any designated k keys are independent random variables.

    Our construction utilises the fact that the output bits of a cryptographic hash function are uniformly distributed,
    independent, binary random variables (well, at least as close to as possible. See [Kaminsky2011]_ for an analysis).
    Thus, slicing the output of a cryptographic hash function into k different slices gives you k independent random
    variables.

    We chose Blake2 as the cryptographic hash function mainly for two reasons:

    * it is fast.
    * in keyed hashing mode, Blake2 provides MACs with just one hash function call instead of the
      two calls in the HMAC construction used in the double hashing scheme.


    .. warning::
       Please be aware that, although this construction makes the attack of [Kroll2015]_ infeasible, it is most likely
       not enough to ensure security. Or in their own words:

         | However, we think that using independent hash functions alone will not be sufficient to ensure security,
           since in this case other approaches (maybe related to or at least inspired through work from the
           area of Frequent Itemset Mining) are promising to detect at least the most frequent atoms automatically.

    :param ngrams: list of n-grams to be encoded
    :param keys: secret key for blake2 as bytes
    :param ks: number of hash functions to use for each ngram
    :param l: length of the output bitarray (has to be a power of 2)
    :param encoding: the encoding to use when turning the ngrams to bytes

    :return: bitarray of length l with the bits set which correspond to the encoding of the ngrams
    """
    key, = keys  # Unpack.

    log_l = int(math.log(l, 2))
    if not 2 ** log_l == l:
        raise ValueError('parameter "l" has to be a power of two for the BLAKE2 encoding, but was: {}'.format(l))
    bf = bitarray(l)
    bf.setall(False)

    # TODO: I think k = 0 was used to ignore a field, but can't we use IgnoreField instead?
    # if k < 1:
    #    return bf

    for m, k in zip(ngrams, ks):
        random_shorts = []  # type: List[int]
        num_macs = (k + 31) // 32
        for i in range(num_macs):
            hash_bytes = blake2b(m.encode(encoding=encoding), key=key, salt=str(i).encode()).digest()
            random_shorts.extend(struct.unpack('32H', hash_bytes))  # interpret hash bytes as 32 unsigned shorts.
        for i in range(k):
            idx = random_shorts[i] % l
            bf[idx] = 1
    return bf


class NgramEncodings(Enum):
    """ The available schemes for encoding n-grams.

    ..
      the slightly awkward looking construction with the calls to partial and the overwrite of __call__ are due to
      compatibility issues with Python 2.7.
    """
    DOUBLE_HASH = partial(double_hash_encode_ngrams)
    """ the initial encoding scheme as described in Schnell, R., Bachteler, T., & Reiher, J. (2011). A Novel
    Error-Tolerant Anonymous Linking Code. Also see :meth:`double_hash_encode_ngrams`"""
    BLAKE_HASH = partial(blake_encode_ngrams)
    """ uses the BLAKE2 hash function, which is one of the fastest modern hash functions, and does less hash function
    calls compared to the DOUBLE_HASH based schemes. It avoids one of the exploitable weaknesses of the DOUBLE_HASH
    scheme. Also see :meth:`blake_encode_ngrams`"""
    DOUBLE_HASH_NON_SINGULAR = partial(double_hash_encode_ngrams_non_singular)
    """ very similar to DOUBLE_HASH, but avoids singularities in the encoding. Also see
    :meth:`double_hash_encode_ngrams_non_singular`"""

    def __call__(self, *args):
        return self.value(*args)

    @classmethod
    def from_properties(cls,
                        schema  # type: Schema
                        ):
        # type: (...) -> Callable[[Iterable[str], Sequence[bytes], int, int, str], bitarray]
        if schema.hash_type == 'doubleHash':
            if schema.hash_prevent_singularity:
                return cls.DOUBLE_HASH_NON_SINGULAR
            else:
                return cls.DOUBLE_HASH
        elif schema.hash_type == 'blakeHash':
            return cls.BLAKE_HASH
        else:
            msg = "Unsupported hash type '{}'".format(schema.hash_type)
            raise ValueError(msg)


def fold_xor(bloomfilter,  # type: bitarray
             folds  # type: int
             ):
    # type: (...) -> bitarray
    """ Performs XOR folding on a Bloom filter.

        If the length of the original Bloom filter is n and we perform
        r folds, then the length of the resulting filter is n / 2 ** r.

        :param bloomfilter: Bloom filter to fold
        :param folds: number of folds

        :return: folded bloom filter
    """

    if len(bloomfilter) % 2 ** folds != 0:
        msg = ('The length of the bloom filter is {length}. It is not '
               'divisible by 2 ** {folds}, so it cannot be folded {folds} '
               'times.'
               .format(length=len(bloomfilter), folds=folds))
        raise ValueError(msg)

    for _ in range(folds):
        bf1 = bloomfilter[:len(bloomfilter) // 2]
        bf2 = bloomfilter[len(bloomfilter) // 2:]

        bloomfilter = bf1 ^ bf2

    return bloomfilter


def crypto_bloom_filter(record,  # type: Sequence[Text]
                        tokenizers,  # type: List[Callable[[Text], Iterable[Text]]]
                        schema,  # type: Schema
                        keys  # type: Sequence[Sequence[bytes]]
                        ):
    # type: (...) -> Tuple[bitarray, Text, int]
    """ Computes the composite Bloom filter encoding of a record.

        Using the method from
        http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

        :param record: plaintext record tuple. E.g. (index, name, dob, gender)
        :param tokenizers: A list of tokenizers. A tokenizer is a function that
            returns tokens from a string.
        :param schema: the schema
        :param keys: Keys for the hash functions as a tuple of lists of bytes.

        :return: 3-tuple:
                - bloom filter for record as a bitarray
                - first element of record (usually an index)
                - number of bits set in the bloomfilter
    """
    hash_l = schema.l * 2 ** schema.xor_folds
    hash_function = NgramEncodings.from_properties(schema)

    bloomfilter = bitarray(hash_l)
    bloomfilter.setall(False)

    for (entry, tokenize, field, key) \
            in zip(record, tokenizers, schema.fields, keys):
        hash_props = field.hashing_properties
        ngrams = [n for n in tokenize(field.format_value(entry))]
        bloomfilter |= hash_function(
            ngrams, key, hash_props.ks(schema, len(ngrams)), hash_l, hash_props.encoding)

    bloomfilter = fold_xor(bloomfilter, schema.xor_folds)

    return bloomfilter, record[0], bloomfilter.count()


def stream_bloom_filters(dataset,  # type: Iterable[Sequence[Text]]
                         keys,  # type: Sequence[Sequence[bytes]]
                         schema  # type: Schema
                         ):
    # type: (...) -> Iterable[Tuple[bitarray, Text, int]]
    """ Compute composite Bloom filters (CLKs) for every record in an iterable dataset.

        :param dataset: An iterable of indexable records.
        :param schema: An instantiated Schema instance
        :param keys: A tuple of two lists of secret keys used in the HMAC.
        :return: Generator yielding bloom filters as 3-tuples
    """
    tokenizers = [tokenizer.get_tokenizer(field.hashing_properties)
                  for field in schema.fields]
    return (crypto_bloom_filter(s, tokenizers, schema, keys)
            for s in dataset)

