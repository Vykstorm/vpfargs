
'''
This module defines all kinds of validators that can be used to validate your function arguments.
'''


from utils import iterable
from inspect import isclass
from copy import copy


class Validator:
    '''
    Base class for all kind of validators
    '''
    def __init__(self):
        pass

    def __call__(self, arg):
        '''
        This method turns the validator to a callable object. It calls check(arg).
        If check(arg) returns something that evaluates to True, this function returns
        the tuple (True, None). This happens when the given argument is valid.
        Otherwise, the tuple (False, error) is fetched (when the arg is invalid). Where 'error'
        will be the value retrieved by the method error_message(arg)
        '''
        result = self.check(arg)
        if result:
            return True, None
        return False, self.error_message(arg)

    def check(self, arg):
        '''
        This method must be implemented by subclasses. It validates the given argument with the validator.
        :param arg: Is the argument to validate.
        :return: Something that evaluates to True if the given argument is valid or not.
        Anything that evaluates to False otherwise.
        '''
        raise NotImplementedError()

    def error_message(self, arg):
        '''
        Retrieves an error message; A brief description explaining why the given argument is not valid.
        This method may be overriden by subclasses
        :param arg:
        :return: Returns a string value, the error message.
        '''
        return ''

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__class__.__name__

    @staticmethod
    def from_object(obj):
        if isinstance(obj, Validator):
            return obj

        # Match any type...
        if type(obj) == object:
            return EmptyValidator()

        # Classes and built-in types.
        if isclass(obj):
            return TypeValidator((obj,))

        # Dictionaries
        if isinstance(obj, dict):
            return ValueValidator(obj)

        # Callables
        if callable(obj):
            return UserValidator(obj)

        # Range objects
        if isinstance(obj, range):
            return RangeValidator(obj)

        # Iterables
        if iterable(obj):
            pass

        # Default validator
        return ValueValidator((obj,))



class TypeValidator(Validator):
    '''
    Validator that check if the given arguments has a proper type.
    '''
    def __init__(self, types, check_subclasses = True, check_bool_subclasses = False):
        '''
        Initializes this instance.
        :param types: Is a list of class objects used for type validation.
        :param check_subclasses: Is a boolean value that indicates how the given argument is checked. If it is True (default value),
        the argument is checked verifying that its type is equal to one of the types specified or a subclass of them.
        This is the default option. Otherwise if its set to False, argument will be validated testing only if its type is the same
        as one of the named classes.
        :param check_bool_type: This has effect only if types includes the 'int' class object and check_subclasses is set to True
        This argument overrides the value of check_subclasses when testing argument type with the bool builin type.
        If its set to True (default Value), boolean values (True and False) are valid numeric values (because bool is a
        subclass of type)
        By default this behaviour is disabled (default value is False)
        '''
        try:
            if not iterable(types):
                raise Exception()
            for cls in types:
                if not isclass(cls):
                    raise Exception()
        except:
            raise TypeError()

        if not isinstance(check_subclasses, bool):
            raise TypeError()
        if not isinstance(check_bool_subclasses, bool):
            raise TypeError()

        super().__init__()

        types = tuple(frozenset(types))
        self.types = tuple(types)
        self.check_subclasses = check_subclasses
        self.check_bool_subclasses = check_bool_subclasses

    def check(self, arg):
        cls = type(arg)
        if not self.check_subclasses or (not self.check_bool_subclasses and cls == bool):
            return cls in self.types
        return isinstance(arg, self.types)

    def error_message(self, arg):
        return 'Type {} expected but got {}'.format(
            ' or '.join([cls.__name__ for cls in self.types]),
            type(arg).__name__)


class ValueValidator(Validator):
    '''
    This is a validator that checks if the given arguments has a valid value.
    '''
    def __init__(self, values, match_types = True):
        '''
        Initializes this validator.
        :param values: Must be a list of all possible values that the given arguments can take in order to pass the
        validation stage. The operator == is used to check if the argument matches with any value in this list.
        :param match_types: If set to True, the argument must have also the same type as the matched value.
        By default is set to True.
        '''
        super().__init__()
        if not iterable(values):
            raise TypeError()
        self.values = tuple(values)
        self.match_types = match_types

    def check(self, arg):
        for value in self.values:
            if arg == value and (not self.match_types or (type(arg) == type(value))):
                return True
        return False

    def error_message(self, arg):
        return 'Value {} expected but got {}'.format(
            ' or '.join([str(value) for value in self.values]),
            str(arg))


class EmptyValidator(Validator):
    '''
    This is a special validator. Is an "empty" validator because all given arguments will pass
    its validation stage.
    '''
    def check(self, arg):
        return True


class RangeValidator(Validator):
    '''
    Validator that checks if the given argument is within a numeric range.
    '''
    def __init__(self, interval, match_types = True):
        '''
        Initializes this instance.
        :param interval: Must be an instance of the built-in class range(). The given argument will pass the validation stage if
        its inside such range (the operator 'in' which uses the method __contains__ is used to check if the argument is contained
        within that range).
        :param match_types: When is set to True, not only the given must be within the range specified, but also need to
        be an int value.
        '''
        if not isinstance(interval, range):
            raise TypeError()
        if not isinstance(match_types, bool):
            raise TypeError()

        super().__init__()
        self.interval = interval
        self.match_types = match_types

    def check(self, arg):
        return arg in self.interval and ((not self.match_types) or (type(arg) == int))

    def error_message(self, arg):
        return 'Value in {} expected but got {}'.format(self.interval, arg)


class UserValidator(Validator):
    '''
    Its a validator defined by the user.
    '''
    def __init__(self, func):
        '''
        Initializes this instance.
        :param predicate: It must be a callable object which accepts the argument to be validated. The result must be
        evaluated to True if the given argument is valid or something that evaluates to False otherwise.
        '''
        super().__init__()
        if not callable(func):
            raise TypeError()
        self.func = func

    def check(self, arg):
        return self.func(arg)

    def error_message(self, arg):
        return 'Expression {}({}) evaluated to False'.format('', str(arg))


class ComposedValidator(Validator):
    '''
    This a kind of validator which are build grouping other validators. The given argument is valid when any of the
    validators that are part of the group are evaluated to True. Otherwise, the argument is not valid.
    '''
    def __init__(self, items=()):
        '''
        Initializes this instance.
        :param items: It can be a list of instances of class Validator.
        '''
        super().__init__()
        self.validators = []
        self.extend(items)

    def add(self, item):
        '''
        Adds another validator.
        :param item: The validator to add (must be an instance of class Validator)
        '''
        if not isinstance(item, Validator):
            raise TypeError()
        if isinstance(item, ComposedValidator):
            self.extend(item)
        else:
            self.validators.append(item)

    def extend(self, items):
        '''
        Add a few more validators to this composed validator
        :param items: It must be an iterable where items must be instances of the class Validator
        :return:
        '''
        if not iterable(items):
            raise TypeError()
        for item in items:
            self.add(item)

    def __copy__(self):
        '''
        Creates a copy of this instance.
        :return: A clone of this object
        '''
        return ComposedValidator(self)

    def __or__(self, other):
        '''
        Creates a new composed validator within the validators in this instance and another validator.
        :param other:
        :return:
        '''
        result = copy(self)
        result |= other
        return result

    def __ior__(self, other):
        '''
        This is equivalent to method add() if the given argument is an instance of class Validator or
        the method extend() if its a sequence of validators or another ComposedValidator object.
        :param other: An instance of class Validator or an iterable of Validator objects.
        '''
        if isinstance(other, Validator):
            self.add(other)
        else:
            self.extend(other)
        return self

    def __iter__(self):
        return iter(self.validators)

    def check(self, arg):
        for validator in self:
            if validator.check(arg):
                return True
        return False
