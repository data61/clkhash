# -*- coding: utf-8 -*-

"""
Functions to tokenize words (PII)
"""
from __future__ import unicode_literals

from typing import Callable, Iterable, Optional, Text

from future.builtins import range

from functools import partial



def get_tokenizer(tok_desc  # type: Dict[str, Any]
                  ):
    # type: (...) -> Callable[[Text, Optional[Text]], Iterable[Text]]
    """ Get tokeniser function from the tokenizer definition in the schema.

        This function takes a dictionary, containing the schema definition. It returns a
        function that takes a string and tokenises based on those properties.
    """

    typ = tok_desc.get('type', None)

    if typ == 'ngram':
        n = tok_desc.get('n')
        if n < 0:
            raise ValueError('`n` in `n`-gram must be non-negative.')
        positional = tok_desc.get('positional')

        return partial(ngram_tokenizer, n=n, positional=positional)
    elif typ == 'exact':
        pass
    else:
        raise ValueError("unsupported tokenization strategy: '{}'".format(typ))


def ngram_tokenizer(word, n, positional, ignore=None,):
    # type: (Text, int, bool, Optional[Text]) -> Iterable[Text]
    """ Produce `n`-grams of `word`.

        :param n: the n in n-gram, non-negative integer
        :param positional: enables positional n-gram tokenization
        :param word: The string to tokenize.
        :param ignore: The substring whose occurrences we remove from
            `word` before tokenization.
        :return: Tuple of n-gram strings.
    """
    if ignore is not None:
        word = word.replace(ignore, '')

    if len(word) == 0:
        return tuple()

    if n > 1:
        word = ' {} '.format(word)

    if positional:
        # These are 1-indexed.
        return ('{} {}'.format(i + 1, word[i:i + n])
                for i in range(len(word) - n + 1))
    else:
        return (word[i:i + n] for i in range(len(word) - n + 1))


def dummy(word, ignore=None):
    # type: (Text, Optional[Text]) -> Iterable[Text]
    """
    Null tokenizer returns empty Iterable.
    FieldSpec Ignore has hashing_properties = None
    and get_tokenizer has to return something for this case,
    even though it's never called. An alternative would be to
    use an Optional[Callable]].
    :param word: not used
    :param ignore: not used
    :return: empty Iterable
    """
    return ('' for i in range(0))

