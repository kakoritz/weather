"""Apply required patches to the p4a recipe.py for the CI build.

Run after cloning p4a to ~/.p4a-py311 and checking out 3762c88c.
Three patches:
  1. PyProjectRecipe: always pass --no-isolation to python -m build
  2. install_hostpython_prerequisites: clean stale .dist-info before upgrade
  3. install_hostpython_prerequisites: add --trusted-host so pip works
     when hostpython3 (p4a's own compiled Python) lacks SSL support
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

# ── Patch 3: use sys.executable (has SSL) instead of hostpython3 (no SSL) ────
# hostpython3 is built without SSL; using sys.executable (the buildozer venv
# Python) lets pip reach PyPI over HTTPS. We still install into hostpython3's
# site_dir with --target and --python-version so wheels are correct.
NEW3 = (
    '        pip_env = self.get_hostrecipe_env()\n'
    '        pip_env["HOME"] = "/tmp"\n'
    '        import sys as _sys\n'
    '        shprint(sh.Command(_sys.executable), "-m", "pip", *pip_options, _env=pip_env)'
)
# Accept both the original and the intermediate trusted-host form as OLD3
OLD3_ORIG = (
    '        pip_env = self.get_hostrecipe_env()\n'
    '        pip_env["HOME"] = "/tmp"\n'
    '        shprint(sh.Command(self.real_hostpython_location), "-m", "pip", *pip_options, _env=pip_env)'
)
OLD3_PREV = (
    '        pip_env = self.get_hostrecipe_env()\n'
    '        pip_env["HOME"] = "/tmp"\n'
    '        pip_options = ["--trusted-host", "pypi.org",\n'
    '                       "--trusted-host", "files.pythonhosted.org"] + pip_options\n'
    '        shprint(sh.Command(self.real_hostpython_location), "-m", "pip", *pip_options, _env=pip_env)'
)
if NEW3 in src:
    print('Patch 3 already applied')
elif OLD3_ORIG in src:
    src = src.replace(OLD3_ORIG, NEW3)
    print('Patch 3 applied: use sys.executable for pip (SSL fix)')
elif OLD3_PREV in src:
    src = src.replace(OLD3_PREV, NEW3)
    print('Patch 3 applied (from trusted-host form): use sys.executable for pip (SSL fix)')
else:
    print('ERROR: Patch 3 target not found', file=sys.stderr)
    sys.exit(1)

open(path, 'w').write(src)
print('recipe.py patched successfully')

# ── Patch 4: build.py — use sys.executable for venv (avoids SSL-less hostpython3)
build_path = os.path.expanduser('~/.p4a-py311/pythonforandroid/build.py')
bsrc = open(build_path).read()

OLD4 = (
    '    # Use our hostpython to create the virtualenv\n'
    '    host_python = sh.Command(ctx.hostpython)\n'
    '    with current_directory(join(ctx.build_dir)):\n'
    '        shprint(host_python, \'-m\', \'venv\', \'venv\')\n'
    '\n'
    '        # Prepare base environment and upgrade pip:\n'
    '        base_env = dict(copy.copy(os.environ))\n'
    '        base_env["PYTHONPATH"] = ctx.get_site_packages_dir(arch)\n'
    '        info(\'Upgrade pip to latest version\')\n'
    '        shprint(sh.bash, \'-c\', (\n'
    '            "source venv/bin/activate && pip install -U pip"\n'
    '        ), _env=copy.copy(base_env))\n'
    '\n'
    '        # Install Cython in case modules need it to build:\n'
    '        info(\'Install Cython in case one of the modules needs it to build\')\n'
    '        shprint(sh.bash, \'-c\', (\n'
    '            "venv/bin/pip install Cython"\n'
    '        ), _env=copy.copy(base_env))'
)
NEW4 = (
    '    # Use sys.executable (has SSL) instead of hostpython3 (no SSL) for the venv\n'
    '    import sys as _sys\n'
    '    host_python = sh.Command(_sys.executable)\n'
    '    with current_directory(join(ctx.build_dir)):\n'
    '        shprint(host_python, \'-m\', \'venv\', \'venv\')\n'
    '\n'
    '        # Prepare base environment and upgrade pip:\n'
    '        base_env = dict(copy.copy(os.environ))\n'
    '        base_env["PYTHONPATH"] = ctx.get_site_packages_dir(arch)\n'
    '        info(\'Upgrade pip to latest version\')\n'
    '        shprint(sh.bash, \'-c\', (\n'
    '            "source venv/bin/activate && pip install -U pip"\n'
    '        ), _env=copy.copy(base_env))\n'
    '\n'
    '        # Install Cython in case modules need it to build:\n'
    '        info(\'Install Cython in case one of the modules needs it to build\')\n'
    '        shprint(sh.bash, \'-c\', (\n'
    '            "venv/bin/pip install Cython"\n'
    '        ), _env=copy.copy(base_env))'
)
if OLD4 not in bsrc:
    if NEW4 in bsrc:
        print('Patch 4 already applied')
    else:
        print('ERROR: Patch 4 target not found in build.py', file=sys.stderr)
        sys.exit(1)
else:
    bsrc = bsrc.replace(OLD4, NEW4)
    open(build_path, 'w').write(bsrc)
    print('Patch 4 applied: use sys.executable for venv (SSL fix in build.py)')
