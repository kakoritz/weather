"""Apply required patches to the p4a recipe.py for the CI build.

Run after cloning p4a to ~/.p4a-py311 and checking out 3762c88c.
Two patches:
  1. PyProjectRecipe: always pass --no-isolation to python -m build
  2. install_hostpython_prerequisites: clean stale .dist-info before upgrade
"""
import os, re, sys

path = os.path.expanduser('~/.p4a-py311/pythonforandroid/recipe.py')
src = open(path).read()

# ── Patch 1: add --no-isolation ──────────────────────────────────────────────
OLD1 = (
    '        build_args = [\n'
    '            "-m",\n'
    '            "build",\n'
    '            "--wheel",\n'
    '            "--config-setting",\n'
    '            "builddir={}".format(sub_build_dir),\n'
    '        ] + self.extra_build_args'
)
NEW1 = (
    '        build_args = [\n'
    '            "-m",\n'
    '            "build",\n'
    '            "--wheel",\n'
    '            "--no-isolation",\n'
    '            "--config-setting",\n'
    '            "builddir={}".format(sub_build_dir),\n'
    '        ] + self.extra_build_args'
)
if OLD1 not in src:
    if NEW1 in src:
        print('Patch 1 already applied')
    else:
        print('ERROR: Patch 1 target not found', file=sys.stderr)
        sys.exit(1)
else:
    src = src.replace(OLD1, NEW1)
    print('Patch 1 applied: --no-isolation')

# ── Patch 2: clean stale dist-info before upgrade ────────────────────────────
OLD2 = (
    '        if force_upgrade:\n'
    '            pip_options.append("--upgrade")'
)
NEW2 = (
    '        if force_upgrade:\n'
    '            pip_options.append("--upgrade")\n'
    '            import glob as _glob, os as _os, re as _re, shutil as _shutil\n'
    '            for _pkg in packages:\n'
    '                _pn = _re.split(r"[>=<!~\\[]", _pkg)[0].strip().replace("-","_").lower()\n'
    '                _site = self._host_recipe.site_dir\n'
    '                try: _entries = _os.listdir(_site)\n'
    '                except OSError: _entries = []\n'
    '                for _e in _entries:\n'
    '                    if _e.lower().startswith(_pn+"-") and _e.endswith(".dist-info"):\n'
    '                        _shutil.rmtree(_os.path.join(_site, _e), ignore_errors=True)'
)
if OLD2 not in src:
    if NEW2 in src:
        print('Patch 2 already applied')
    else:
        print('ERROR: Patch 2 target not found', file=sys.stderr)
        sys.exit(1)
else:
    src = src.replace(OLD2, NEW2)
    print('Patch 2 applied: dist-info cleanup')

open(path, 'w').write(src)
print('recipe.py patched successfully')
