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

import csv
import json
import math
import os
import pkgutil
import random
from datetime import datetime, timedelta
from typing import (Iterable, List, Optional,
                    Sequence, TextIO, Tuple, Union)

from future.builtins import range

from clkhash.field_formats import FieldSpec
from clkhash import schema


def load_csv_data(resource_name):
    # type: (str) -> List[str]
    """ Loads first column of specified CSV file from package data.
    """
    data_bytes = pkgutil.get_data('clkhash', 'data/{}'.format(resource_name))
    if data_bytes is None:
        raise ValueError("No data resource found with name {}".format(resource_name))
    else:
        data = data_bytes.decode('utf8')
        reader = csv.reader(data.splitlines())
        next(reader, None)  # skip the headers
        return [row[0] for row in reader]


def save_csv(data,  # type: Iterable[Tuple[Union[str, int], ...]]
             headers,  # type: Iterable[str]
             file  # type: TextIO
             ):
    # type: (...) -> None
    """
    Output generated data to file as CSV with header.

    :param data: An iterable of tuples containing raw data.
    :param headers: Iterable of feature names
    :param file: A writeable stream in which to write the CSV
    """

    print(','.join(headers), file=file)
    writer = csv.writer(file)
    writer.writerows(data)


def random_date(start, end):
    # type: (datetime, datetime) -> datetime
    """ Generate a random datetime between two datetime objects.

    :param start: datetime of start
    :param end: datetime of end
    :return: random datetime between start and end
    """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)


class NameList:
    """ Randomly generated PII records.
    """

    randomname_schema_bytes = pkgutil.get_data('clkhash', 'data/randomnames-schema.json')
    if randomname_schema_bytes is None:
        raise Exception("Couldn't locate package data. Please file a bug report.")
    randomname_schema = json.loads(randomname_schema_bytes.decode())
    SCHEMA = schema.from_json_dict(randomname_schema)

    def __init__(self, n):
        # type: (int) -> None
        self.load_names()

        self.earliest_birthday = datetime(year=1916, month=1, day=1)
        self.latest_birthday = datetime(year=2016, month=1, day=1)

        self.names = [person for person in self.generate_random_person(n)]

        self.all_male_first_names = None  # type: Optional[Sequence[str]]
        self.all_female_first_names = None  # type: Optional[Sequence[str]]
        self.all_last_names = None  # type: Optional[Sequence[str]]

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
        assert self.all_male_first_names is not None
        assert self.all_female_first_names is not None
        assert self.all_last_names is not None
        for i in range(n):
            sex = 'M' if random.random() > 0.5 else 'F'
            dob = random_date(self.earliest_birthday, self.latest_birthday).strftime("%Y/%m/%d")
            first_name = random.choice(self.all_male_first_names) if sex == 'M' else random.choice(
                self.all_female_first_names)
            last_name = random.choice(self.all_last_names)

            yield (
                str(i),
                first_name + ' ' + last_name,
                dob,
                sex
            )

    def load_names(self):
        # type: () -> None
        """ Loads a name database from package data

        Uses data files sourced from
        http://www.quietaffiliate.com/free-first-name-and-last-name-databases-csv-and-sql/
        """

        self.all_male_first_names = load_csv_data('male-first-names.csv')
        self.all_female_first_names = load_csv_data('female-first-names.csv')
        self.all_last_names = load_csv_data('CSV_Database_of_Last_Names.csv')

    def generate_subsets(self, sz, overlap=0.8, subsets=2):
        # type: (int, float, int) -> Tuple[List, ...]
        """ Return random subsets with nonempty intersection.

            The random subsets are of specified size. If an element is
            common to two subsets, then it is common to all subsets.
            This overlap is controlled by a parameter.

            :param sz: size of subsets to generate
            :param overlap: size of the intersection, as fraction of the
                subset length
            :param subsets: number of subsets to generate

            :raises ValueError: if there aren't sufficiently many names
                in the list to satisfy the request; more precisely,
                raises if (1 - subsets) * floor(overlap * sz)
                              + subsets * sz > len(self.names).

            :return: tuple of subsets
        """
        overlap_sz = int(math.floor(overlap * sz))
        unique_sz = sz - overlap_sz  # Unique names per subset
        total_unique_sz = unique_sz * subsets  # Uniques in all subsets
        total_sz = overlap_sz + total_unique_sz

        if total_sz > len(self.names):
            msg = 'insufficient names for requested size and overlap'
            raise ValueError(msg)

        sset = random.sample(self.names, total_sz)

        # Overlapping subset, pool of unique names
        sset_overlap, sset_unique = sset[:overlap_sz], sset[overlap_sz:]
        assert len(sset_unique) == subsets * unique_sz

        # Split pool of unique names into `subsets` chunks
        uniques = (sset_unique[p * unique_sz: (p + 1) * unique_sz]
                   for p in range(subsets))

        return tuple(sset_overlap + u for u in uniques)
