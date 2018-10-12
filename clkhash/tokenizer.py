# -*- coding: utf-8 -*-

"""
Functions to tokenize words (PII)
"""
from __future__ import unicode_literals

from typing import Callable, Iterable, Optional, Text

from future.builtins import range

from clkhash import field_formats


def get_tokenizer(fhp  # type: Optional[field_formats.FieldHashingProperties]
                  ):
    # type: (...) -> Callable[[Text, Optional[Text]], Iterable[Text]]
    """ Get tokeniser function from the hash settings.

        This function takes a FieldHashingProperties object. It returns a
        function that takes a string and tokenises based on those properties.
    """

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

    if not fhp:
        return dummy

    n = fhp.ngram
    if n < 0:
        raise ValueError('`n` in `n`-gram must be non-negative.')

    positional = fhp.positional

    def tok(word, ignore=None):
        # type: (Text, Optional[Text]) -> Iterable[Text]
        """ Produce `n`-grams of `word`.

            :param word: The string to tokenize.
            :param ignore: The substring whose occurrences we remove from
                `word` before tokenization.
            :return: Tuple of n-gram strings.
        """
        if ignore is not None:
            word = word.replace(ignore, '')

        if n > 1:
            word = ' {} '.format(word)

        if positional:
            # These are 1-indexed.
            return ('{} {}'.format(i + 1, word[i:i + n])
                    for i in range(len(word) - n + 1))
        else:
            return (word[i:i + n] for i in range(len(word) - n + 1))

    return tok
