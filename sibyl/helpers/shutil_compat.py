import shutil
import sys


def copytree(src, dst, symlinks=False, ignore=None, dirs_exist_ok=False):
    # if python version is 3.8 or higher, use the built-in copytree
    if sys.version_info >= (3, 8):
        shutil.copytree(
            src, dst, symlinks=symlinks, ignore=ignore, dirs_exist_ok=dirs_exist_ok
        )
    else:
        from distutils import dir_util

        dir_util.copy_tree(src, dst)
