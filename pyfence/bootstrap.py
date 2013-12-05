import sys

import pyfence
from pyfence.compat import *
from pyfence.core import fence_namespace, module_eligible
from pyfence.log import error, debug


def parse_options(options):
    known_options = [
        'off',
        'on',
        'stop',
        'strict',
        'include',
        'exclude',
        'lint',
        'debug',
    ]

    for arg in sys.argv:
        if arg.startswith('--fence:'):
            sys.argv.remove(arg)
            new_options = arg.split(':')[1].split(',')
            for option in new_options:
                name = option if not '=' in option else option.split('=')[0]
                if not name in known_options:
                    error('Unknown option "%s"' % option)
                    sys.exit(1)
                else:
                    if '=' in option:
                        name, value = option.split('=')[:2]
                        options[name] = value
                    else:
                        options[option] = True



def install_import_hook():
    original_importer = builtins.__import__

    def importer(*args, **kwargs):
        m = original_importer(*args, **kwargs)
        if module_eligible(m) and not pyfence.options['off']:
            debug('Importing %s' % (m.__name__))
            fence_namespace(m)
        return m

    builtins.__import__ = importer    
    debug('Import hook installed')