import abc
from typing import Iterable, Text, Dict, Any, Optional


class AbstractComparison(metaclass=abc.ABCMeta):
    """ Abstract base class for all comparisons """

    @abc.abstractmethod
    def tokenize(self, word: str) -> Iterable[str]:
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

    def __init__(self, n: int, positional: Optional[bool] = False) -> None:
        if n < 0:
            raise ValueError('`n` in `n`-gram must be non-negative.')
        self.n = n
        self.positional = positional

    def tokenize(self, word: str) -> Iterable[str]:
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
            return (f'{i + 1} {word[i:i + self.n]}'
                    for i in range(len(word) - self.n + 1))
        else:
            return (word[i:i + self.n] for i in range(len(word) - self.n + 1))

    def __repr__(self):
        return f'NgramComparison(n={self.n}, positional={self.positional})'


class ExactComparison(AbstractComparison):
    """ Enables exact comparisons

    High similarity score if inputs are identical, low otherwise.

    Internally, this is done by treating the whole input as one token. Thus, if you have chosen the 'bitsPerToken'
    strategy for hashing, you might want to adjust the value such that the corresponding feature gets an appropriate
    representation in the filter.
    """

    def tokenize(self, word: str) -> Iterable[str]:
        if len(word) == 0:
            return tuple()
        else:
            return word,


class NumericComparison(AbstractComparison):
    """ enables numerical comparisons of integers or floating point numbers.

    The numerical distance between two numbers relate to the similarity of the tokens produces by this comparison class.
    We implemented the idea of Vatsalan and Christen (Privacy-preserving matching of similar patients, Journal of
    Biomedical Informatics, 2015).

    The basic idea is to encode a number's neighbourhood such that the neighbourhoods of close numbers overlap.
    For example, the neighbourhood of x=21 is 19, 20, 21, 22, 23, and the neighbourhood of y=23 is 21, 22, 23, 24, 25.
    These two neighbourhoods share three elements. The overlap of the neighbourhoods of two numbers increases the closer
    the numbers are to each other.

    There are two parameters to control the overlap.

    - `threshold_distance`: the maximum distance which leads to an non-empty overlap. Neighbourhoods for points which
                          are further apart have no elements in common. (*)

    - `resolution`: controls how many tokens are generated. (the `b` in the paper). Given an interval of size
                    `threshold_distance` we create 'resolution tokens to either side of the mid-point plus one token for
                    the mid-point. Thus, 2 * `resolution` + 1 tokens in total. A higher resolution differentiates better
                    between different values, but should be chosen such that it plays nicely with the overall Bloom
                    filter size and insertion strategy.

    (*) the reality is a bit more tricky. We first have to quantize the inputs to multiples of `threshold_distance` /
    (2 * `resolution`), in order to get comparable neighbourhoods.
    For example, if we choose a `threshold_distance` of 8 and a `resolution` of 2, then, without quantization, the
    neighbourhood of x=25 would be [21, 23, 25, 27, 29] and for y=26 [22, 24, 26, 28, 30], resulting in no overlap.
    The quantization ensures that the inputs are mapped onto a common grid. In our example, the values would be
    quantized to even numbers (multiples of 8 / (2 * 2) = 2). Thus x=25 would be mapped to 26.
    The quantization has the side effect that sometimes two values which are further than `threshold_distance` but not
    more than `threshold_distance` + 1/2 quantization level apart can share a common token. For instance, a=24.99 would
    be mapped to 24 with a neighbourhood of [20, 22, 24, 26, 28], and b=16 neighbourhood is [12, 14, 16, 18, 20].

    We produce the output tokens based on the neighbourhood in the following way. Instead of creating a neighbourhood
    around the quantized input with values dist_interval = `threshold_distance` / (2 * `resolution`) apart, we instead
    multiply all values by (2 * `resolution`). This saves the division, which can introduce numerical inaccuracies.
    Thus, the tokens for x=25 are [88, 96, 104, 112, 120].

    We are dealing with floating point numbers by quantizing them to integers by multiplying them with
    10 ** `fractional_precision` and then rounding them to the nearest integer.

    Thus, we don't support to full range of floats, but the subset between
    2.2250738585072014e-(308 - fractional_precision - log(resolution, 10)) and
    1.7976931348623157e+(308 - fractional_precision - log(resolution, 10))

    :ivar threshold_distance: maximum detectable distance. Points that are further apart won't have tokens in common.
    :ivar resolution: controls the amount of generated tokens. Total number of tokens will be 2 * resolution + 1
    :ivar fractional_precision: number of digits after the point to be considered
    """

    def __init__(self, threshold_distance: float, resolution: int, fractional_precision: int = 0) -> None:
        # check that there is enough precision to have non-zero threshold_distance
        if not threshold_distance > 0:
            raise ValueError(f'threhold_distance has to be positive, but was {threshold_distance}')
        if resolution < 1:
            raise ValueError(f'resolution has to be greater than zero, but was {resolution}')
        if fractional_precision < 0:
            raise ValueError(f'fractional_precision cannot be less than zero, but was {fractional_precision}')
        # instead of dividing threshold distance as in the paper, we rather multiply the inputs by 'resolution' and then
        # use threshold_distance as distance_interval (saves a division which would need more precision)
        self.distance_interval = int(round(threshold_distance * pow(10, fractional_precision)))
        if self.distance_interval == 0:
            raise ValueError('not enough fractional precision to encode threshold_distance')
        self.resolution = resolution
        self.fractional_precision = fractional_precision

    def tokenize(self, word: str) -> Iterable[str]:
        if len(word) == 0:
            return tuple()
        try:
            v = int(word, base=10)  # we try int first, so we don't loose precision
            if self.fractional_precision > 0:
                v *= pow(10, self.fractional_precision)
        except ValueError:
            v_float = float(word)
            if self.fractional_precision > 0:
                v = int(round(v_float * pow(10, self.fractional_precision)))
            else:
                v = int(v_float)
        v = v * 2 * self.resolution
        residue = v % self.distance_interval

        if residue == 0:
            v = v
        elif residue < self.distance_interval / 2:
            v = v - residue
        else:
            v = v + (self.distance_interval - residue)
        return [str(v + i * self.distance_interval) for i in
                range(-self.resolution, self.resolution + 1)]


class NonComparison(AbstractComparison):
    """
    Non comparison.
    """

    def tokenize(self, word: str) -> Iterable[str]:
        """ Null tokenizer returns empty Iterable.

        FieldSpec Ignore has hashing_properties = None
        and get_tokenizer has to return something for this case,
        even though it's never called. An alternative would be to
        use an Optional[Callable]].

        :param word: not used
        :return: empty Iterable
        """
        return ('' for i in range(0))


def get_comparator(comp_desc: Dict[str, Any]) -> AbstractComparison:
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
        return NumericComparison(threshold_distance=comp_desc.get('thresholdDistance', -1),
                                 resolution=comp_desc.get('resolution', -1),
                                 fractional_precision=comp_desc.get('fractional_precision', 0))
    else:
        raise ValueError(f"unsupported comparison strategy: '{typ}'")
