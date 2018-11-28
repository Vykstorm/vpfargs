
from itertools import count
from inspect import signature
from utils import iterable
from types import MethodType
from validators import Validator, EmptyValidator
from functools import update_wrapper
from exceptions import ValidationError, ParsingError
from processors import Processor, ProcessorBundle



class Wrapper(ProcessorBundle):
    '''
    A instance of this class encapsulates a method (Acts like a function wrapper)
    wrappers
    '''
    def __init__(self, func):
        '''
        Initializes this instance.
        :param func: Must be a callable object. A regular function, lambda or a class object with the instance method
        __call__
        '''
        if not callable(func):
            raise TypeError()

        super().__init__()
        self.wrapped_func = func
        self.signature = signature(func, follow_wrapped=True)
        update_wrapper(self, func) # This method sets some attributes to introspect the wrapper object like __qualname__

    def call_wrapped(self, *args, **kwargs):
        '''
        Calls the wrapped function with the given arguments.
        :param args:
        :param kwargs:
        :return:
        '''
        return self.wrapped_func(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        '''
        This method make instances of this class callable.
        When called, first it processes its input values calling process_input() as if the wrapped function was called
        with such arguments.

        After that, the wrapped method is called with the processed input values.
        Finally, the output values are processed and returned by this function.

        :param args: Positional arguments to be passed to the wrapped method (they will be processed using the method
        process_input() )
        :param kwargs: Keyword arguments to be passed to the wrapped method (they will be processed using the method
        process_input() )
        :return: Returns what the wrapped function outputs but before that, those values will be processed using the method
        process_output()
        '''
        bounded_args = self.signature.bind(*args, **kwargs)
        bounded_args.apply_defaults()

        args = bounded_args.args
        output = self.call_wrapped(*self.process_input(*args))

        if not iterable(output):
            output = tuple() if output is None else (output, )

        output = self.process_output(*output)

        if iterable(output):
            if len(output) == 0:
                return None
            return tuple(output) if len(output) > 1 else next(iter(output))
        return output

    def __get__(self, instance, owner):
        '''
        Turns instances of this class to non-data descriptors. This is used when this class is returned when decorating
        a class or instance method. When calling the decorated function, __get__ is called and it will return a method bounded
        to the given instance.
        :param instance:
        :param owner:
        :return:
        '''
        if instance is None:
            return self
        return MethodType(self, instance)

    def __str__(self):
        return str(self.wrapped_func)

    def __repr__(self):
        return repr(self.wrapped_func)

class Parser:
    '''
    Base class for InputParser and OutputParser
    '''
    def __init__(self, items):
        if not iterable(items):
            raise TypeError()
        if not all(map(lambda item: callable(item), items)):
            raise TypeError()
        self.items = tuple(items)

    def parse(self, *args):
        if len(self.items) != len(args):
            raise ValueError()

        result = []
        for item, index, arg in zip(self.items, count(start=0), args):
            try:
                result.append(item(arg))
            except Exception as e:
                raise ParsingError(index, str(e))
        return result



class ParseInput(Parser, Processor):
    '''
    Represents a processor which parses inputs values with the given items.
    '''
    def __init__(self, items):
        Processor.__init__(self)
        Parser.__init__(self, items)

    def process_input(self, *args):
        return self.parse(*args)


class ParseOutput(Parser, Processor):
    '''
    Represents a processor which parses output values with the given items.
    '''
    def __init__(self, items):
        Processor.__init__(self)
        Parser.__init__(self, items)

    def process_output(self, *args):
        return self.parse(*args)


class ValidateInput(ParseInput):
    '''
    Its a processor which validates the input values using the given validators.
    '''
    def __init__(self, items):
        '''
        Initializes this instance.
        :param items: Must be an iterable list with Validator instance objects to validate the input values.
        '''
        if not iterable(items) and not isinstance(items, Validator):
            raise TypeError()
        if isinstance(items, Validator) and not all(map(lambda item: isinstance(item, Validator), items)):
            raise TypeError()
        validators = items
        super().__init__([validator.simplify() for validator in validators])

    def validate(self, *args):
        for validator, index, arg in zip(self.items, count(start=0), args):
            valid, error = validator(arg)
            if not valid:
                raise ValidationError(index, error)

    def parse(self, *args):
        if len(self.items) != len(args):
            raise ValueError()
        self.validate(*args)
        return args


class Decorator:
    '''
    Base class for ValidateinputDecorator and ParseInputDecorator
    '''
    empty_arg = None

    def __init__(self, *args, **kwargs):
        '''
        Initializes this instance.
        :param args: Positional arguments indicated in the decorator.
        :param kwargs: Keyword arguments indicated in the decorator.
        '''
        self.args, self.kwargs = args, kwargs

    def __call__(self, f):
        '''
        This is called when this decorator is used to decorate the given function.
        :param f: The function to decorate (Must be a callable object)
        :return: Returns a function wrapper (instance of the class Wrapper)
        '''
        if not callable(f):
            raise TypeError()

        args, kwargs = self.args, self.kwargs

        s = signature(f, follow_wrapped=True)
        s = s.replace(parameters=[param.replace(default=self.empty_arg) for param in s.parameters.values()])
        bounded_args = s.bind(*args, **kwargs)
        bounded_args.apply_defaults()

        processor = self.create_processor(*bounded_args.args)
        wrapper = Wrapper(f) if not isinstance(f, Wrapper) else f
        wrapper.append(processor)
        return wrapper

    def create_processor(self, *args):
        raise NotImplementedError()


class ValidateInputDecorator(Decorator):
    '''
    A decorator to add input values validation feature.
    '''
    empty_arg = object

    def create_processor(self, *args):
        return ValidateInput(map(Validator.from_spec, args))


class ParseInputDecorator(Decorator):
    '''
    A decorator to add input values parsing feature
    '''
    empty_arg = None

    def create_processor(self, *args):
        return ParseInput([arg if arg is not None else lambda arg: arg for arg in args])



# Alias of class ValidateInputDecorator
validate = ValidateInputDecorator

# Alias of class ParseInputDecorator
parse = ParseInputDecorator

