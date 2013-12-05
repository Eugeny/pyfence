import inspect
import logging
import sys

import pyfence


def log(message, level):
    if not sys.stdout.isatty():
        print(message)
        return

    s = ' *** PyFence '
    l = ''
    
    if level == logging.DEBUG:
        l = '\033[37mDEBUG\033[0m '
    if level == logging.WARNING:
        l = '\033[33mWARN\033[0m  '
    if level == logging.ERROR:
        l = '\033[31mERROR\033[0m '

    s += l.ljust(9)
    s += message

    print(s)


def debug(message):
    if pyfence.options['debug']:
        log(message, logging.DEBUG)


def warn(message):
    log(message, logging.WARNING)


def error(message):
    log(message, logging.ERROR)


def log_failure_header():
    error('---------------------------')
    error('PyFence verification failed')


def log_function_location(obj):
    try:
        error('in %s:%i' % (inspect.getsourcefile(obj), inspect.getsourcelines(obj)[1]))
    except IOError:
        error('in unknown location - %s' % repr(obj))


def log_function_call(fqn, args, kwargs):
    argstrs = [repr(x) for x in args] + ['%s=%s' % (k, repr(kwargs[k])) for k in kwargs]
    error(' :: %s(%s)' % (fqn, ', '.join(argstrs)))
