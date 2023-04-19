from importlib import metadata

from . import bloomfilter, field_formats, key_derivation, schema, randomnames, describe
from .schema import Schema

try:
    __version__ = metadata.version('clkhash')
except metadata.PackageNotFoundError:
    __version__ = "development"

__author__ = "Data61"
