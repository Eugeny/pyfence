import sys
import types

if sys.version_info[0] < 3:
    import __builtin__
    builtins = __builtin__
else:
    import builtins
    types.ClassType = types.TypeType = type
    unicode = str
