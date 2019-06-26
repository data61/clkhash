import pkg_resources

from . import bloomfilter, field_formats, key_derivation, schema, randomnames, describe
from .schema import Schema

try:
    __version__ = pkg_resources.get_distribution('clkhash').version
except pkg_resources.DistributionNotFound:
    __version__ = "development"

__author__ = "Data61"
