import os
import sys
import tempfile


class temporary_file(object):
    """
    A cross platform temporary secure file context manager.

    Usage:

        with temporary_file() as filename:
            # open and use the file at filename

        # file is now deleted

    """

    def __enter__(self):
        self.os_fd, self.tmpfile_name = tempfile.mkstemp(text=True)
        return self.tmpfile_name

    def __exit__(self, *exc):
        os.close(self.os_fd)
        os.remove(self.tmpfile_name)


def create_temp_file(suffix=None):
    """
    Creates, opens and returns a temporary file.
    Note this file will not be automatically deleted by Python.
    """
    os_fd, filename = tempfile.mkstemp(suffix=suffix, text=True)
    if sys.version_info[0] >= 3:
        return open(filename, 'wt', encoding='utf8', newline='')
    else:
        return open(filename, 'wt')