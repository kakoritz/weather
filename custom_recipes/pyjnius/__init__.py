"""Custom pyjnius recipe pinned to 1.6.1.

pyjnius 1.7.0 (default in p4a 3762c88c) requires Cython~=3.1.2 in its
pyproject.toml [build-system] requires. Kivy requires Cython<=3.0.0.
These are mutually exclusive; no single Cython version satisfies both.

pyjnius 1.6.1 requires only 'Cython' (no version constraint) which
is compatible with the Cython 3.0.0 installed for Kivy.
"""
from pythonforandroid.recipes.pyjnius import PyjniusRecipe as _Base


class PyjniusRecipe(_Base):
    version = '1.6.1'
    url = 'https://github.com/kivy/pyjnius/archive/{version}.zip'
    hostpython_prerequisites = ["setuptools>=58.0.0", "wheel", "Cython"]

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        import os
        # pyjnius 1.6.1 uses 'long' as a Python type in jnius_utils.pxi.
        # Cython 3.0 on Python 3 doesn't recognise 'long' as a builtin.
        # Patch: add 'long = int' alias at the top of jnius_utils.pxi.
        pxi = os.path.join(
            self.get_build_dir(arch.arch), 'jnius', 'jnius_utils.pxi'
        )
        if not os.path.exists(pxi):
            return
        content = open(pxi).read()
        if 'long = int' not in content:
            content = '# Python 3 compat\nlong = int\n\n' + content
            open(pxi, 'w').write(content)
            print(f'Patched {pxi}: added long = int')


recipe = PyjniusRecipe()
