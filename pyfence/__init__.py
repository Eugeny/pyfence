from collections import defaultdict

from pyfence.bootstrap import parse_options, install_import_hook
from pyfence.core import fence_function, fence_namespace


__version__ = '0.1.1'


options = defaultdict(bool)

parse_options(options)

if not options['off']:
    install_import_hook()


__all__ = [
    '__version__',
    'options',
    'fence_function',
    'fence_namespace',
]