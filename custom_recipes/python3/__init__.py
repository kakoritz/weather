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


recipe = Python3RecipeAndroid()
