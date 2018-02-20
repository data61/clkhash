# -*- coding: utf-8 -*-

"""
Functions to tokenize words (PII)
"""
from __future__ import unicode_literals

import functools
from typing import AnyStr, Callable, Text, Iterable

from clkhash import field_formats


def tokenize(n, positional, word):
    # type: (int, bool, Text) -> Iterable[Text]
    """ Produce `n`-grams of `word`.

        :param n: Length of `n`-grams.
        :param positional: If `True`, then include the index of the
            substring with the `n`-gram.
        :raises ValueError: When `n` is negative.
    """
    if n < 0:
        raise ValueError('`n` in `n`-gram must be non-negative.')

    if n >= 1:
        word = ' {} '.format(word)

    if positional:
        # Why do these have to be 1-indexed??
        return ('{} {}'.format(i + 1, word[i:i+n])
                for i in range(len(word) - n + 1))
    else:
        return (word[i:i+n] for i in range(len(word) - n + 1))



def get_tokenizer(hash_settings  # type: field_formats.FieldHashingProperties
                  ):
    # type: (...) -> Callable[[Text], Iterable[Text]]
    n = hash_settings.ngram
    p = hash_settings.positional

    return functools.partial(tokenize, n, p)
