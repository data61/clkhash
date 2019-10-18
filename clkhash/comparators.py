# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import abc
import decimal
from decimal import Decimal
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


class NumericComparison(AbstractComparison):
    """ enables numerical comparisons of integers or floating point numbers.

    The numerical distance between two numbers relate to the similarity of the tokens produces by this comparison class.
    We implemented the idea of Vatsalan and Christen (Privacy-preserving matching of similar patients, Journal of
    Biomedical Informatics, 2015).

    The basic idea is to encode a number's neighbourhood. Such that the neighbourhoods of close numbers overlap.
    For example, the tokens for x=21 are 19, 20, 21, 22, 23, and the tokens for y=23 are 21, 22, 23, 24, 25. Then the
    two sets of tokens share three elements. It is easy to see that two numbers have more tokens in common the closer
    they are to each other.

    There are two parameter to control the overlap.
    - threshold_distance: the maximum distance which leads to at least one common token. The token sets for points which
                          are further apart have no elements in common. (*)
    - resolution: controls how many tokens are generated. (the 'b' in the paper). Given an interval of size
                  'threshold_distance' we create 'resolution tokens to either side of the mid-point plus one token for
                  the mid-point. Thus,  2 * resolution + 1 tokens in total. A higher resolution differentiates better
                  between different values, but should be chosen such that it plays nicely with the overall Bloom filter
                  size and insertion strategy.

    (*) the reality is a bit more tricky. Depending on the choice of parameters we first have to quantize the inputs, in
    order to get comparable tokens. For example, if we choose a 'threshold_distance' of 8 and a 'resolution' of 2, then
    the tokens for x=25 would be [21, 23, 25, 27, 29] and for y=26 [22, 24, 26, 28, 30], resulting in sets with no
    common element. The quantization ensures that the inputs are mapped onto a common grid. In our example, the values
    would be quantized to even numbers. Thus x=25 would be mapped to 26, and z=24.99 would be mapped to 24.
    The quantization has the side effect that sometimes two values who are further than 'threshold_distance' but not
    more than 'threshold_distance' + 1/2 quantization level apart can share a common token.

    :ivar threshold_distance: maximum detectable distance. Points that are further apart won't have tokens in common.
    :ivar resolution: controls the amount of generated tokens. Total number of tokens will be 2 * resolution + 1
    """

    def __init__(self, threshold_distance, resolution):
        # type: (str, int) -> None
        self.threshold_distance = Decimal(threshold_distance)
        self.resolution = resolution
        self.distance_interval = self.threshold_distance
        self.min_prec = self._get_precision(self.threshold_distance)
        self.resolution_prec = self._get_precision(Decimal(resolution))

    @staticmethod
    def _get_precision(x):  # type: (Decimal) -> int
        return len(x.as_tuple().digits)

    def tokenize(self, word):  # type: (Text) -> Iterable[Text]
        v = Decimal(word)
        # we have to adjust the precision of the Decimal context such that we don't get rounding, because that might
        # lead to slightly different tokens
        v_prec = self._get_precision(v)
        if decimal.getcontext().prec < sum((v_prec, self.min_prec, self.resolution_prec, 5)):
            decimal.getcontext().prec = sum((v_prec, self.min_prec, self.resolution_prec, 5))
        v = v * 2 * self.resolution
        residue = v % self.distance_interval
        # that is not a proper mod function above. negative numbers have a negative residue
        if residue < 0:
            residue += self.distance_interval
        if residue == 0.0:
            v = v
        elif residue < self.distance_interval / 2:
            v = v - residue
        else:
            v = v + (self.distance_interval - residue)
        return [str((v + i * self.distance_interval).normalize()) for i in range(-self.resolution, self.resolution + 1)]


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
    elif typ == 'numeric':
        return NumericComparison(threshold_distance=comp_desc.get('thresholdDistance'),
                                 resolution=comp_desc.get('resolution'))
    else:
        raise ValueError("unsupported comparison strategy: '{}'".format(typ))
