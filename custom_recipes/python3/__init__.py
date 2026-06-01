"""Custom Python 3 recipe for Android builds.

Adds configure cache variables that tell autoconf setgrent/getgrent/endgrent
do not exist on Android (they were never in Android's Bionic libc). Without
this, Python 3.11's grpmodule.c compiles with undeclared function calls and
fails with -Werror,-Wimplicit-function-declaration on any recent NDK.
"""
from pythonforandroid.recipes.python3 import Python3Recipe


class Python3RecipeAndroid(Python3Recipe):
    configure_args = list(Python3Recipe.configure_args) + [
        # Python builds grp module if grp.h is found, regardless of individual
        # function checks. Android Bionic has grp.h but lacks the enumerate
        # functions. Setting header=no prevents grp module from being built at all.
        'ac_cv_header_grp_h=no',
        'ac_cv_func_setgrent=no',
        'ac_cv_func_getgrent=no',
        'ac_cv_func_endgrent=no',
    ]


recipe = Python3RecipeAndroid()
