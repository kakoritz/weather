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


class Python3RecipeAndroid(Python3Recipe):
    configure_args = list(Python3Recipe.configure_args) + [
        # Suppress grp module — grpmodule.c calls setgrent/getgrent/endgrent
        # unconditionally (not behind HAVE_* guards). These don't exist in Bionic.
        'ac_cv_header_grp_h=no',
    ]

    def get_recipe_env(self, arch, with_flags_in_cc=True):
        env = super().get_recipe_env(arch, with_flags_in_cc)
        # Android Bionic lacks many POSIX functions Python probes for.
        # NDK 25b clang treats implicit-function-declaration as an error.
        # Downgrade to warning so Python builds degrade gracefully.
        env['CFLAGS'] = env.get('CFLAGS', '') + ' -Wno-error=implicit-function-declaration'
        return env


recipe = Python3RecipeAndroid()
