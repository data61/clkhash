import abc
import re
import string

from future.utils import raise_from, with_metaclass

class InvalidEntryError(Exception):
    pass


class FieldValidator(with_metaclass(abc.ABCMeta, object)):
    @abc.abstractmethod
    def __init__(self, properties):
        pass

    @abc.abstractmethod
    def __call__(self, str_in):
        pass


class StringValidator(FieldValidator):
    def __init__(self, properties):
        # TODO: What do I do with this?? The encoding is specified when
        #       the file is opened...
        self.encoding = properties['encoding']
        # TODO: This should be precompiled for efficiency.
        if 'pattern' in properties:
            self.pattern = properties['pattern']
        else:
            self.case = properties.get('case', 'mixed')
            self.minLength = properties.get('minLength')
            self.maxLength = properties.get('maxLength')

    def __call__(self, str_in):
        if hasattr(self, 'pattern'):
            raise NotImplementedError('Pattern validation not implemented.')
        else:
            if self.minLength and len(str_in) < self.minLength:
                raise InvalidEntryError('Expected string length of at least '
                                        '{}. Read string of length {}.'
                                        .format(self.minLength, len(str_in)))

            if self.maxLength and len(str_in) > self.maxLength:
                raise InvalidEntryError('Expected string length of at most '
                                        '{}. Read string of length {}.'
                                        .format(self.maxLength, len(str_in)))

            if self.case == 'upper':
                if str_in.upper() != str_in:
                    raise InvalidEntryError('Expected upper case string. Read '
                                            '{}.'.format(str_in))
            elif self.case == 'lower':
                if str_in.lower() != str_in:
                    raise InvalidEntryError('Expected lower case string. Read '
                                            '{}.'.format(str_in))
            elif self.case == 'mixed':
                pass
            else:
                raise ValueError('Invalid case property {}.'.format(self.case))


class IntegerValidator(FieldValidator):
    def __init__(self, properties):
        self.minimum = properties.get('minimum')
        self.maximum = properties.get('maximum')

    def __call__(self, str_in):
        if not all(str_in in string.digits):
            raise InvalidEntryError('Expected integer to consist of numerical '
                                    'characters only. Read "{}".'
                                    .format(str_in))
        value = int(str_in)

        if self.minimum is not None and value < self.minimum:
            raise InvalidEntryError('Expected integer value of at least {}.'
                                    'Read {}.'.format(value))

        if self.maximum is not None and value > self.minimum:
            raise InvalidEntryError('Expected integer value of at most {}.'
                                    'Read {}.'.format(value))


class DateValidator(FieldValidator):
    def __init__(self, properties):
        self.format = properties['format']

    def __call__(self, str_in):
        if self.format == 'rfc3339':
            # TODO: This should be precompiled for efficiency.
            if re.match(r'^\d\d\d\d-\d\d-\d\d$', str_in) is None:
                raise InvalidEntryError('Date expected to conform to '
                                        'RFC3339. Read {}.'.format(str_in))
            try:
                datetime.strptime(str_in, '%Y-%m-%d')
            except ValueError as e:
                raise_from(InvalidEntryError('Invalid date. Read {}.'
                                             .format(str_in)),
                           e)

        else:
            raise ValueError('Unrecognised date format: {}.'
                             .format(self.format))


class EnumValidator(FieldValidator):
    def __init__(self, properties):
        self.values = set(properties['enum'])

    def __call__(self, str_in):
        if str_in not in self.values:
            raise InvalidEntryError('Expected enum value is one of {}. Read '
                                    '{}.'.format(str_in))
