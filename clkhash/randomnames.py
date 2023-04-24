"""
Module to produce a dataset of names, genders and dates of birth and manipulate that list

Names and ages are based on Australian and USA census data, but are not correlated.
Additional functions for manipulating the list of names
- producing reordered and subset lists with a specific overlap

ClassList class - generate a list of length n of [id, name, dob, gender] lists

TODO: Generate realistic errors
TODO: Add RESTful api to generate reasonable name data as requested
"""
import bisect
import csv
import json
import math
import pkgutil
import random
from datetime import date, datetime, timedelta
from typing import (Iterable, List, Optional,
                    Sequence, TextIO, Tuple, Union)

from clkhash.field_formats import FieldSpec
from clkhash import schema


def save_csv(data: Iterable[Tuple[Union[str, int], ...]],
             headers: Iterable[str],
             file: TextIO
             ) -> None:
    """
    Output generated data to file as CSV with header.

    :param data: An iterable of tuples containing raw data.
    :param headers: Iterable of feature names
    :param file: A writeable stream in which to write the CSV
    """

    print(','.join(headers), file=file)
    writer = csv.writer(file)
    writer.writerows(data)


def random_date(year: int, age_distribution: Optional['Distribution']) -> datetime:
    """ Generate a random datetime between two datetime objects.

    :param start: datetime of start
    :param end: datetime of end
    :return: random datetime between start and end
    """
    if not age_distribution:
        raise ValueError("Age distribution must be created before creating a random date.")
    try:
        age = int(age_distribution.generate())
    except ValueError:
        raise ValueError("Values in age distribution tables must be integers.")

    start = datetime(year=year - age, month=1, day=1)
    end = datetime(year=year - age + 1, month=1, day=1)

    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)


class Distribution:
    """Creates a random value generator with a weighted distribution
    """

    def __init__(self, resource_name: str) -> None:
        self.total = 0
        self.indices = []  # type: List[int]
        self.values = []  # type: List[str]
        self.load_csv_data(resource_name)
        self.length = len(self.values)
        if not self.length:
            raise ValueError("Distribution table must have a record.")

    def load_csv_data(self, resource_name: str) -> None:
        """ Loads the first two columns of the specified CSV file from package data.
        The first column represents the value and the second column represents the count in the population.
        """

        data_bytes = pkgutil.get_data('clkhash', f'{resource_name}')
        if not data_bytes:
            raise ValueError(f"No data resource found with name {resource_name}")
        data = data_bytes.decode('utf8')
        reader = csv.reader(data.splitlines())
        next(reader, None)  # skip the headers
        for row in reader:
            try:
                self.total += int(row[1])
            except ValueError:
                raise ValueError("Distribution resources must only contain integers in the second column.")
            self.indices.append(self.total)
            self.values.append(row[0])

    def generate(self) -> str:
        """ Generates a random value, weighted by the known distribution
        """

        target = random.randint(0, self.total - 1)
        return self.values[bisect.bisect_left(self.indices, target)]


class NameList:
    """ Randomly generated PII records.
    """

    randomname_schema_bytes = pkgutil.get_data('clkhash', 'data/randomnames-schema-v2.json')
    if randomname_schema_bytes is None:
        raise Exception("Couldn't locate package data. Please file a bug report.")
    randomname_schema = json.loads(randomname_schema_bytes.decode())
    SCHEMA = schema.from_json_dict(randomname_schema)

    def __init__(self, n: int) -> None:
        self.load_data()

        self.year = date.today().year - 1

        self.names = [person for person in self.generate_random_person(n)]

        self.all_male_first_names = None  # type: Optional[Distribution]
        self.all_female_first_names = None  # type: Optional[Distribution]
        self.all_last_names = None  # type: Optional[Distribution]
        self.all_ages = None  # type: Optional[Distribution]

    @property
    def schema_types(self) -> Sequence[FieldSpec]:
        return self.SCHEMA.fields

    def generate_random_person(self, n: int) -> Iterable[Tuple[str, str, str, str]]:
        """
        Generator that yields details on a person with plausible name, sex and age.

        :yields: Generated data for one person
            tuple - (id: str, name: str('First Last'), birthdate: str('DD/MM/YYYY'), sex: str('M' | 'F') )
        """
        assert self.all_male_first_names is not None
        assert self.all_female_first_names is not None
        assert self.all_last_names is not None
        for i in range(n):
            sex = 'M' if random.random() > 0.5 else 'F'
            dob = random_date(self.year, self.all_ages).strftime("%Y/%m/%d")
            first_name = self.all_male_first_names.generate() if sex == 'M' else self.all_female_first_names.generate()
            last_name = self.all_last_names.generate()

            yield (
                str(i),
                first_name + ' ' + last_name,
                dob,
                sex
            )

    def load_data(self) -> None:
        """ Loads databases from package data

        Uses data files sourced from
        http://www.quietaffiliate.com/free-first-name-and-last-name-databases-csv-and-sql/
        https://www.census.gov/topics/population/genealogy/data/2010_surnames.html
        https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/3101.0Jun%202016
        """

        self.all_male_first_names = Distribution('data/male-first-names.csv')
        self.all_female_first_names = Distribution('data/female-first-names.csv')
        self.all_last_names = Distribution('data/last-names.csv')
        self.all_ages = Distribution('data/ages.csv')

    def generate_subsets(self, sz: int, overlap: float = 0.8, subsets: int = 2) -> Tuple[List, ...]:
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
            raises if (1 - subsets) * floor(overlap * sz) + subsets * sz > len(self.names).

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
