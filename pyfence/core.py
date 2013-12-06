import inspect
import itertools
import re
import types
import sys

import pyfence
from pyfence.compat import *
from pyfence.log import warn, error, debug, log_function_call, log_failure_header, log_function_location


def abort():
    error('Aborting')
    sys.exit(1)


def validate_single_type(srctype, target):
    """
    Compares a type against a string description

    :param srctype: source type
    :param target: srctype pattern
    """

    if type(target) is not str:
        # comparing type objects
        if srctype is target:
            return True
    else:
        if '.' in target:
            # comparing FQNs
            fqn = srctype.__module__ + '.' + srctype.__name__
            return target == fqn
        else:
            # comparing class names
            return srctype.__name__ == target

    return False


def validate_type(srctype, targets):
    """
    Compares type and its bases against a typelist string description

    :param srctype: source type
    :param target: typelist pattern
    """
    if not hasattr(srctype, 'mro') or pyfence.options['strict']:
        candidates = [srctype]
    else:
        if srctype is type:
            candidates = type.mro(srctype)
        else:
            candidates = srctype.mro()

    for src_type in candidates:
        for target in targets:
            if validate_single_type(src_type, target):
                return True
    return False


def extract_argument(argument_name, fx, args, kwargs):
    """
    Locates value for argument ``name`` in ``args`` and ``kwargs`` for a call of function ``fx``
    """
    argspec = inspect.getargspec(fx)
    num_normal_args = len(argspec.args) - len(argspec.defaults or [])

    arg_index = argspec.args.index(argument_name)
    if argument_name in kwargs:
        value = kwargs[argument_name]
    elif arg_index >= num_normal_args:
        return argspec.defaults[arg_index - num_normal_args]
    else:
        value = args[arg_index]
    return value


def parse_type_spec(spec):
    targets = map(str.strip, spec.split(','))

    # Map common "meta-types"
    specs = {
        'class': [types.TypeType],
        'any': [object],
        'str': [basestring],
        'None': [type(None)],
        'function': ['function', 'instancemethod', 'staticmethod', 'classmethod']
    }

    targets = itertools.chain(*[specs.get(x, [x]) for x in targets])
    targets = [
        x.split('`')[1] if type(x) is str and x.startswith(':class')
        else x 
        for x in targets
    ]
    return targets


def extract_requirements(fx, fqn):
    doc = fx.__doc__
    described_arguments = []
    reqs = {
        'argument_types': {},
        'return_type': None,
        'raises': [],
    }

    lines = []
    for l in doc.splitlines():
        l = l.strip()
        if l.startswith(':'):
            original = l
            l = l[1:]
            if ':' in l:
                params, value = l.split(':', 1)
                params = params.split()
                value = value.strip()
                lines.append((params, value, original))

    argspec = inspect.getargspec(fx)

    for params, value, original in lines:
        if not params:
            continue
        if params[0] == 'param':
            if len(params) < 2:
                warn(fqn)
                warn('Broken argument entry for %s: %s' % (repr(fx), repr(original)))
                continue
            if len(params) == 2:
                described_arguments.append(params[1])
            else:
                described_arguments.append(params[2])
                reqs['argument_types'][params[2]] = parse_type_spec(params[1])

        if params[0] == 'type':
            if len(params) < 2:
                warn(fqn)
                warn('Broken argument type entry for %s: %s' % (repr(fx), repr(original)))
                continue

            argument_name = params[1]
            if not argument_name in argspec.args:
                warn(fqn)
                warn('Argument %s not present in %s' % (repr(argument_name), repr(fx)))
                continue

            reqs['argument_types'][argument_name] = parse_type_spec(value)

        if params[0] == 'rtype':
            reqs['return_type'] = parse_type_spec(value)

        if params[0] in ['raises', 'raise', 'except', 'exception']:
            reqs['raises'] += parse_type_spec(value)

    if pyfence.options['lint']:
        for argument in described_arguments:
            if not argument in reqs['argument_types']:
                warn(fqn)
                warn('No type specified for argument %s' % repr(argument))
    return reqs


def fence_function(fx, parent=None, fqn=None):
    """
    Returns a fenced wrapper for a function ``fx`` or None if function shouldn't / couldn't be fenced

    :param fx: function
    :param parent: (optional) containing class
    :param fqn: fully qualified name
    """

    if not fx.__doc__:
        return None
    
    is_classmethod = False
    if hasattr(fx, 'im_self') and fx.im_self is not None:
        is_classmethod = True
        fx = fx.im_func

    is_staticmethod = False
    if type(fx) is staticmethod:
        is_staticmethod = True

    try:
        args = inspect.getargspec(fx).args
    except TypeError:
        return None

    requirements = extract_requirements(fx, fqn)
    
    def wrapper(*args, **kwargs):
        for argument in requirements['argument_types']:
            value = extract_argument(argument, fx, args, kwargs)
            required_type = requirements['argument_types'][argument]
            if not validate_type(type(value), required_type):
                log_failure_header()
                log_function_call(fqn, args, kwargs)
                log_function_location(fx)
                error('%s was %s (%s) instead of %s' % (
                    argument, repr(value), type(value).__name__, required_type
                ))
                if pyfence.options['stop']:
                    abort()

        try:
            out = fx(*args, **kwargs)
        except Exception as ex:
            if len(requirements['raises']) == 0:
                raise
            for required_type in requirements['raises']:
                if validate_type(type(ex), [required_type]):
                    raise
            else:
                log_failure_header()
                log_function_call(fqn, args, kwargs)
                log_function_location(fx)
                error(repr(ex))
                error('%s was thrown (only %s allowed)' % (
                    type(ex).__name__, requirements['raises']
                ))
                if pyfence.options['stop']:
                    abort()
                raise

        if requirements['return_type'] is not None:
            required_type = requirements['return_type']
            if not validate_type(type(out), required_type):
                log_failure_header()
                log_function_call(fqn, args, kwargs)
                log_function_location(fx)
                error('Return value was %s (%s) instead of %s' % (
                    repr(out), type(out).__name__, required_type
                ))
                if pyfence.options['stop']:
                    abort()

        return out

    final_wrapper = wrapper

    # Retain self argument
    # Some code might check the name of the first argument later; it must remain 'self' if it was
    if len(args) > 0 and args[0] == 'self':
        def instance_wrapper(self, *args, **kwargs):
            return wrapper(*([self] + list(args)), **kwargs)
        final_wrapper = instance_wrapper

    if is_classmethod:
        def class_wrapper(cls, *args, **kwargs):
            return wrapper(*([cls] + list(args)), **kwargs)
        final_wrapper = classmethod(class_wrapper)

    if is_staticmethod:
        final_wrapper = staticmethod(wrapper)

    return final_wrapper


FENCE_TAG = '_processed_by_fence'


def fence_namespace(m, stack=None, fqn=None):
    """
    Fences contents of namespace (module or class)

    :param m: namespace
    :param fqn: fully qualified name
    """
    if hasattr(m, FENCE_TAG):
        return

    if hasattr(m, '__module__'):
        if not module_eligible(m.__module__):
            return

    try:
        setattr(m, FENCE_TAG, True)
    except TypeError:
        pass

    stack = stack or []

    if not stack:
        fqn = m.__name__

    debug('Processing %s (%s)' % (fqn, m))

    for key in m.__dict__:
        if key.startswith('__') and key.endswith('__'):
            continue

        if not hasattr(m, key):
            continue

        if hasattr(m, '__dict__'):
            value = m.__dict__[key]
        else:
            value = getattr(m, key)

        if hasattr(value, '__module__'):
            if not module_eligible(value.__module__):
                continue

        if value in stack:
            continue

        if type(value) in [types.ClassType, types.TypeType]:
            fence_namespace(value, stack + [value], fqn + '.' + value.__name__)

        if type(value) in [types.MethodType, types.FunctionType]:
            fenced = fence_function(value, parent=m, fqn=fqn+'.'+value.__name__)
            if fenced is not None:
                setattr(m, key, fenced)


def module_eligible(m):
    """
    Checks whether a module is eligible for fencing (i.e. included and not excluded)
    """

    if m is None:
        return False

    if type(m) not in [unicode, str]:
        m = m.__name__

    if pyfence.options.get('exclude', ''):
        for pattern in pyfence.options.get('exclude', '').split(':'):
            if re.match('^.*%s.*$' % pattern , m):
                return False

    if not pyfence.options.get('include', ''):
        return True

    for pattern in pyfence.options.get('include', '').split(':'):
        if re.match('^%s.*$' % pattern , m):
            return True

    return False
