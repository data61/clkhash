# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import abc
from typing import Iterable, Text, Dict, Any, Optional

from future.builtins import range
from six import add_metaclass


@add_metaclass(abc.ABCMeta)
class AbstractComparison(object):
    """ Abstract base class for all comparisons """

    @abc.abstractmethod
    def tokenize(self, word):
        # type: (Text) -> Iterable[Text]
        """ The tokenization function.

        Takes a string and returns an iterable of tokens (as strings). This should be
        implemented in a way that the intersection of two sets of tokens produced by this function approximates
        the desired comparison criteria.

        :param word: The string to tokenize.
        :return: Iterable of tokens.
        """
        pass


class NgramComparison(AbstractComparison):
    """ Enables 'n'-gram comparison for approximate string matching. An n-gram is a contiguous sequence of n items
        from a given text.

        For Example: the 2-grams of 'clkhash' are ' c', 'cl', 'lk', 'kh', 'ha', 'as', 'sh', 'h '. Note the white-
        space in the first and last token. They serve the purpose to a) indicate the beginning and end of a word, and b)
        gives every character in the input text a representation in two tokens.

        'n'-gram comparison of strings is tolerant to spelling mistakes, e.g., the strings 'clkhash' and 'clkhush' have
        6 out of 8 2-grams in common. One wrong character will affect 'n' 'n'-grams. Thus, the larger you choose 'n',
        the more the error propagates.

        A positional n-gram also encodes the position of the n-gram within the word. The positional 2-grams of
        'clkhash' are '1  c', '2 cl', '3 lk', '4 kh', '5 ha', '6 as', '7 sh', '8 h '. Positional n-grams can be useful
        for comparing words where the position of the characters are important, e.g., postcodes or phone numbers.

        :ivar n: the n in n-gram, non-negative integer
        :ivar positional: enables positional n-gram tokenization
        """

    def __init__(self, n, positional=False):
        # type: (int, Optional[bool]) -> None
        if n < 0:
            raise ValueError('`n` in `n`-gram must be non-negative.')
        self.n = n
        self.positional = positional

    def tokenize(self, word):
        # type: (Text) -> Iterable[Text]
        """ Produce `n`-grams of `word`.

        :param word: The string to tokenize.
        :return: Iterable of n-gram strings.
        """
        if len(word) == 0:
            return tuple()

        if self.n > 1:
            word = '{}{}{}'.format(' ' * (self.n - 1), word, ' ' * (self.n - 1))

        if self.positional:
            # These are 1-indexed.
            return ('{} {}'.format(i + 1, word[i:i + self.n])
                    for i in range(len(word) - self.n + 1))
        else:
            return (word[i:i + self.n] for i in range(len(word) - self.n + 1))

    def __repr__(self):
        return 'NgramComparison(n={}, positional={})'.format(self.n, self.positional)


class ExactComparison(AbstractComparison):
    """ Enables exact comparisons

    High similarity score if inputs are identical, low otherwise.

    Internally, this is done by treating the whole input as one token. Thus, if you have chosen the 'fixed k' strategy
    for hashing, you might want to adjust the 'k' value such that the value gets an appropriate representation in the
    filter.
    """

    def tokenize(self, word):  # type: (Text) -> Iterable[Text]
        return word,


class NonComparison(AbstractComparison):
    """
    Non comparison.
    """

    def tokenize(self, word):
        # type: (Text) -> Iterable[Text]
        """ Null tokenizer returns empty Iterable.

        FieldSpec Ignore has hashing_properties = None
        and get_tokenizer has to return something for this case,
        even though it's never called. An alternative would be to
        use an Optional[Callable]].

        :param word: not used
        :return: empty Iterable
        """
        return ('' for i in range(0))


def get_comparator(comp_desc):
    # type: (Dict[str, Any]) -> AbstractComparison
    """ Creates the comparator as defined in the schema. A comparator provides a tokenization method suitable for
    that type of comparison.

    This function takes a dictionary, containing the schema definition. It returns a subclass of AbstractComparison.
    """

    typ = comp_desc.get('type', None)

    if typ == 'ngram':
        return NgramComparison(comp_desc.get('n', -1), comp_desc.get('positional'))
    elif typ == 'exact':
        return ExactComparison()
    else:
        raise ValueError("unsupported comparison strategy: '{}'".format(typ))
