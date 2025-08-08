# kiro/__init__.py
# Shim loader: makes `import kiro...` point to `.kiro/...`

import os
import pkgutil

# Path to the hidden .kiro folder
_here = os.path.dirname(__file__)
dot_kiro = os.path.normpath(os.path.abspath(os.path.join(_here, '..', '.kiro')))

# Add .kiro to the search path for this package
if os.path.isdir(dot_kiro) and dot_kiro not in __path__:
    __path__.insert(0, dot_kiro)

__all__ = [name for _, name, _ in pkgutil.iter_modules(__path__)]

