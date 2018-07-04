import os
import sys
import tempfile
import clkhash

SIMPLE_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__),
    'testdata',
    'simple-schema.json'
)
SAMPLE_DATA_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__),
    'testdata',
    'dirty-data-schema.json'
)

RANDOMNAMES_SCHEMA_PATH = os.path.join(
    os.path.dirname(clkhash.__file__),
    'data',
    'randomnames-schema.json'
)

SAMPLE_DATA_PATH_1 = os.path.join(os.path.dirname(__file__), 'testdata', 'dirty_1000_50_1.csv')
SAMPLE_DATA_PATH_2 = os.path.join(os.path.dirname(__file__), 'testdata', 'dirty_1000_50_2.csv')


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


def create_temp_file(suffix=''):
    """
    Creates, opens and returns a temporary file.
    Note this file will not be automatically deleted by Python.
    """
    os_fd, filename = tempfile.mkstemp(suffix=suffix, text=True)
    if sys.version_info[0] >= 3:
        return open(filename, 'wt', encoding='utf8', newline='')
    else:
        return open(filename, 'wt')
