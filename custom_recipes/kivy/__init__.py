"""Custom Kivy recipe — adds --no-isolation to the build command.

python-for-android builds Kivy via `python -m build --wheel`. By default
this creates an isolated pip environment to install build deps. Our Python
was built with --without-ensurepip, so the venv can't bootstrap pip and
setuptools.build_meta fails to import.

--no-isolation bypasses the isolated env and uses the p4a-managed Python
directly, where setuptools is already installed as a recipe dependency.
"""
from pythonforandroid.recipes.kivy import KivyRecipe as _KivyRecipe


class KivyRecipe(_KivyRecipe):
    extra_build_args = ['--no-isolation']


recipe = KivyRecipe()
