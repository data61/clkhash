import math
from typing import Sequence, Union


class OnlineMeanVariance(object):

    def __init__(self):
        # type: (...) -> None
        self.t = 0  # type: Union[int, float]
        self.n = 0  # type: int
        self.S = 0  # type: float

    def update(self,
               x  # type: Sequence[Union[int, float]]
               ):
        # type: (...) -> None
        """
        updates the statistics with the given list of numbers

        It uses an online algorithm which uses compensated summation to reduce numerical errors.
        See https://angelacorasaniti.wordpress.com/2015/05/06/hw2-mean-and-variance-of-data-stream/ for details.

        :param x: list of numbers
        :return: nothing
        """
        if any(math.isnan(float(i)) or math.isinf(float(i)) for i in x):
            raise ValueError('input contains non-finite numbers like "nan" or "+/- inf"')
        t = sum(x)
        m = float(len(x))
        norm_t = t / m
        S = sum((xi - norm_t) ** 2 for xi in x)
        if self.n == 0:
            self.S = self.S + S
        else:
            self.S = self.S + S + self.n / (m * (m + self.n)) * (m / self.n * self.t - t) ** 2
        self.t = self.t + t
        self.n = self.n + len(x)

    def mean(self):
        # type: (...) -> float
        """
        returns the mean

        :return: the mean
        """
        if self.n == 0:
            return 0
        return self.t / float(self.n)

    def variance(self):
        # type: (...) -> float
        """
        returns the variance

        :return: the variance
        """
        if self.n <= 1:
            return 0
        return self.S / (self.n - 1.)

    def std(self):
        # type: (...) -> float
        """
        returns the standard deviation

        :return: the standard deviation
        """
        return math.sqrt(self.variance())
