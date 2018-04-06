import pkg_resources

from . import bloomfilter
from . import field_formats
from . import key_derivation
from . import schema
from . import randomnames

try:
    __version__ = pkg_resources.get_distribution('clkhash').version
except pkg_resources.DistributionNotFound:
    __version__ = "development"

__author__ = 'N1 Analytics'
