# -*- coding: utf-8 -*-

"""
Functions to tokenize words (PII)
"""
from __future__ import unicode_literals

import functools
from typing import AnyStr, Callable, Iterable, Optional, Text

from future.builtins import range

from clkhash import field_formats


def tokenize(n, positional, word, ignore=None):
    # type: (int, bool, Text, Optional[Text]) -> Iterable[Text]
    """ Produce `n`-grams of `word`.

        :param n: Length of `n`-grams.
        :param positional: If `True`, then include the index of the
            substring with the `n`-gram.
        :param word: The string to tokenize.
        :param ignore: The substring whose occurrences we remove from
            `word` before tokenization.
        :raises ValueError: When `n` is negative.
        :return: Tuple of n-gram strings.
    """
    if n < 0:
        raise ValueError('`n` in `n`-gram must be non-negative.')

    if ignore is not None:
        word = word.replace(ignore, '')

    if n > 1:
        word = ' {} '.format(word)

    if positional:
        # These are 1-indexed.
        return ('{} {}'.format(i + 1, word[i:i+n])
                for i in range(len(word) - n + 1))
    else:
        return (word[i:i+n] for i in range(len(word) - n + 1))



def get_tokenizer(hash_settings  # type: field_formats.FieldHashingProperties
                  ):
    # type: (...) -> Callable[[Text], Iterable[Text]]
    """ Get tokeniser function from the hash settings.

        This function takes a FieldHashingProperties object. It returns a
        function that takes a string and tokenises based on those properties.
    """
    n = hash_settings.ngram
    p = hash_settings.positional

    return functools.partial(tokenize, n, p)
