# -*- coding: utf-8 -*-

from typing import Optional

class HashingProperties(object):
    def __init__(self,
                 k,  # type: Optional[int]
                 hash_type,  # type: str
                 hash_prevent_singularity=None  # type: Optional[bool]
                 ):
        # type: (...) -> None
        """Properties that are global for v1 schema, but per field in v2 schema.
            :param k: The number of bits of the hash to set per ngram.
            :param hash_type: The hashing function to use. Choices are
                'doubleHash' and 'blakeHash'.
            :param hash_prevent_singularity: Ignored unless hash_type is
                'doubleHash'. Prevents bloom filter collisions in certain
                cases when True.
        """
        self.k = k
        self.hash_type = hash_type
        self.hash_prevent_singularity = (
            False
            if hash_prevent_singularity is None and hash_type == 'doubleHash'
            else hash_prevent_singularity)
