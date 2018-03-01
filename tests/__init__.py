import os
import tempfile


class temporary_file(object):
    """
        A cross platform temporary file context manager.

        Usage:

            with temporary_file() as filename:
                # use the file

            # file is now deleted

        We don't use NamedTemporaryFile as it can't be opened multiple times on windows
        #return tempfile.NamedTemporaryFile()

        :return: (file name)
        """

    def __enter__(self):
        self.os_fd, self.tmpfile_name = tempfile.mkstemp(text=True)
        return self.tmpfile_name

    def __exit__(self, *exc):
        os.close(self.os_fd)
        os.remove(self.tmpfile_name)


def create_temp_file():
    os_fd, filename = tempfile.mkstemp(text=True)
    return open(filename, 'wt', encoding='utf8', newline='')