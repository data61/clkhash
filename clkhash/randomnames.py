"""
Module to produce a dataset of names, genders and dates of birth and manipulate that list

Currently very simple and not realistic. Additional functions for manipulating the list of names
- producing reordered and subset lists with a specific overlap

ClassList class - generate a list of length n of [id, name, dob, gender] lists

TODO: Get age distribution right by using a mortality table
TODO: Get first name distributions right by using distributions
TODO: Generate realistic errors
TODO: Add RESTfull api to generate reasonable name data as requested
"""
from __future__ import print_function

import base64
import csv
from datetime import datetime, timedelta
import math
import os
import pkgutil
import random
import re
from typing import Dict, Iterable, List, Sequence, TextIO, Tuple, Union

from future.builtins import range

from clkhash.schema import Schema
from clkhash.field_formats import FieldSpec

def load_csv_data(resource_name):
    # type: (str) -> List[str]
    """Loads a specified CSV data file and returns the first column as a Python list
    """
    data_bytes = pkgutil.get_data('clkhash', 'data/{}'.format(resource_name))
    if data_bytes is None:
        raise ValueError("No data resource found with name {}".format(resource_name))
    else:
        data = data_bytes.decode('utf8')
        reader = csv.reader(data.splitlines())
        next(reader, None)  # skip the headers
        return [row[0] for row in reader]


def save_csv(data,      # type: Iterable[Tuple[Union[str, int], ...]]
             headers,   # type: Iterable[str]
             file       # type: TextIO
             ):
    # type: (...) -> None
    """
    Output generated data to file as CSV with header.

    :param data: An iterable of tuples containing raw data.
    :param schema: Iterable of schema definition dicts
    :param file: A writeable stream in which to write the CSV
    """

    print(','.join(headers), file=file)
    writer = csv.writer(file)
    writer.writerows(data)


def random_date(start, end):
    # type: (datetime, datetime) -> datetime
    """
    This function will return a random datetime between two datetime objects.

    :param start: datetime of start
    :param end: datetime of end
    :return: random datetime between start and end
    """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)


class NameList:
    """ List of randomly generated names.
    """

    with open(os.path.join(os.path.dirname(__file__),
                           'data',
                           'randomnames-schema.json')) as f:
        SCHEMA = Schema.from_json_file(f)
    del f

    def __init__(self, n):
        # type: (int) -> None
        self.load_names()

        self.earliest_birthday = datetime(year=1916, month=1, day=1)
        self.latest_birthday = datetime(year=2016, month=1, day=1)

        self.names = [person for person in self.generate_random_person(n)]

    @property
    def schema_types(self):
        # type: () -> Sequence[FieldSpec]
        return self.SCHEMA.fields

    def generate_random_person(self, n):
        # type: (int) -> Iterable[Tuple[str, str, str, str]]
        """
        Generator that yields details on a person with plausible name, sex and age.

        :yields: Generated data for one person
            tuple - (id: int, name: str('First Last'), birthdate: str('DD/MM/YYYY'), sex: str('M' | 'F') )
        """
        for i in range(n):
            sex = 'M' if random.random() > 0.5 else 'F'
            dob = random_date(self.earliest_birthday, self.latest_birthday).strftime("%Y/%m/%d")
            first_name = random.choice(self.all_male_first_names) if sex == 'M' else random.choice(self.all_female_first_names)
            last_name = random.choice(self.all_last_names)

            yield (
                str(i),
                first_name + ' ' + last_name,
                dob,
                sex
            )

    def load_names(self):
        # type: () -> None
        """
        This function loads a name database into globals firstNames and lastNames

        initial version uses data files from
        http://www.quietaffiliate.com/free-first-name-and-last-name-databases-csv-and-sql/

        """

        self.all_male_first_names = load_csv_data('male-first-names.csv')
        self.all_female_first_names = load_csv_data('female-first-names.csv')
        self.all_last_names = load_csv_data('CSV_Database_of_Last_Names.csv')

    def generate_subsets(self, sz, overlap=0.8):
        """
        Return a pair of random subsets of the name list with a specified
        proportion of elements in common.

        :param sz: length of subsets to generate
        :param overlap: fraction of the subsets that should have the same names in them
        :raises ValueError: if there aren't sufficiently many names in the list to satisfy
            the request; more precisely, raises if sz + (1 - overlap)*sz > n = len(self.names)
        :return: pair of subsets
        """
        notoverlap = sz - int(math.floor(overlap * sz))
        total_sz = sz + notoverlap
        if total_sz > len(self.names):
            raise ValueError('Requested subset size and overlap demands more '
                             + 'than the number of available names')
        sset = random.sample(self.names, total_sz)
        return sset[:sz], sset[notoverlap:]
