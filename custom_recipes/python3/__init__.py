"""Custom Python 3 recipe for Android builds.

NDK 25b's clang treats implicit function declarations as hard errors
(-Werror,-Wimplicit-function-declaration). Android Bionic is missing many
POSIX functions that Python 3.11 probes for (setgrent, getgrouplist,
initgroups, getloadavg, etc.). Rather than suppress each function
individually, we add -Wno-error=implicit-function-declaration to CFLAGS
so the Python build degrades gracefully for missing Bionic symbols.

We also suppress grp.h detection so Python skips building grpmodule
entirely (grpmodule.c calls enumerate functions unconditionally, not
behind HAVE_* guards, so the CFLAGS workaround alone is insufficient).
"""
from pythonforandroid.recipes.python3 import Python3Recipe


_ANDROID_MISSING = [
    # grp module — calls these unconditionally (not behind HAVE_* guards)
    'ac_cv_header_grp_h=no',
    'ac_cv_func_setgrent=no',
    'ac_cv_func_getgrent=no',
    'ac_cv_func_endgrent=no',
    # posixmodule.c — group management not in Bionic API 24
    'ac_cv_func_getgrouplist=no',
    'ac_cv_func_initgroups=no',
    'ac_cv_func_setgroups=no',
    # Shadow passwords — not in Bionic
    'ac_cv_func_getspnam=no',
    'ac_cv_func_getspent=no',
    # System load — not in Bionic
    'ac_cv_func_getloadavg=no',
    # getlogin() removed; getlogin_r() is present
    'ac_cv_func_getlogin=no',
    # Pseudo-terminals — unreliable on Android
    'ac_cv_func_openpty=no',
    'ac_cv_func_forkpty=no',
    # BSD-specific flags / attrs not on Android
    'ac_cv_func_chflags=no',
    'ac_cv_func_lchflags=no',
    'ac_cv_func_lchmod=no',
    # BSD kqueue — not on Android
    'ac_cv_func_kqueue=no',
]


class Python3RecipeAndroid(Python3Recipe):
    configure_args = list(Python3Recipe.configure_args) + _ANDROID_MISSING

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        import os
        # Python 3.11 does not honour Setup.local *disabled* for stdlib modules.
        # Patch grpmodule.c directly: wrap the group-enumerate block (setgrent /
        # getgrent / endgrent) in #ifndef __ANDROID__ so it compiles to a no-op
        # that returns an empty list. Android Bionic never had these functions.
        grp_c = os.path.join(
            self.get_build_dir(arch.arch), 'Modules', 'grpmodule.c'
        )
        if not os.path.exists(grp_c):
            return
        src = open(grp_c).read()
        old = (
            '    setgrent();\n'
            '    while ((p = getgrent()) != NULL) {\n'
            '        PyObject *v = mkgrent(module, p);\n'
            '        if (v == NULL || PyList_Append(d, v) != 0) {\n'
            '            Py_XDECREF(v);\n'
            '            Py_DECREF(d);\n'
            '            endgrent();\n'
            '            return NULL;\n'
            '        }\n'
            '        Py_DECREF(v);\n'
            '    }\n'
            '    endgrent();'
        )
        new = (
            '#ifndef __ANDROID__\n'
            '    setgrent();\n'
            '    while ((p = getgrent()) != NULL) {\n'
            '        PyObject *v = mkgrent(module, p);\n'
            '        if (v == NULL || PyList_Append(d, v) != 0) {\n'
            '            Py_XDECREF(v);\n'
            '            Py_DECREF(d);\n'
            '            endgrent();\n'
            '            return NULL;\n'
            '        }\n'
            '        Py_DECREF(v);\n'
            '    }\n'
            '    endgrent();\n'
            '#endif /* __ANDROID__ */'
        )
        if old in src:
            open(grp_c, 'w').write(src.replace(old, new))
        else:
            # Already patched or different version — leave it alone
            pass


recipe = Python3RecipeAndroid()
