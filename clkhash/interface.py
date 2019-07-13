from abc import abstractmethod


class EncodingProgressInterface:
    """Abstract class for presenting encoding progress.
    """

    @abstractmethod
    def __init__(self, length):
        # type: (int) -> None
        pass

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        # type: (...) -> None
        pass

    @abstractmethod
    def callback(self, tics, clk_stats):
        """Callback method called by the encoder to update progress.

        :param tics: Number of records completed
        :param clk_stats: Statistics about the completed records
        :return:
        """
        pass
