"""This module provides functionality for handling frozen python scripts
   and modules and appending them to the resulting image.

   Copyright (c) 2016 Braiins Systems s.r.o.
"""
import os
import sys

import sbbs.verbosity
import SCons.Scanner

from micropython.utils import get_tool_pathname

class FrozenDirsNotAllowed(SCons.Warnings.Warning):
    pass

def generate(env):
    """
    Updates construction environment for qstring generation
    """
    env.AddMethod(FrozenScripts, 'FrozenScripts')


def FrozenScripts(env, dir, target='frozen_scripts.c', ):
    """
    """
    if not SCons.Util.is_List(dir):
        dir = [dir]

    if len(dir) > 1:
        raise SCons.Errors.StopError(FrozenDirsNotAllowed,
                                     'Only 1 frozen script directory can be '
                                     'specified, provided: %s'
                                     '(%s)' % (len(dir), dir))

    # NOTE: we cannot use $SOURCES since the script really wants only a
    # directory. This causes problems when using variant_dir builds as
    # $SOURCES is expanded into $VARIANT_DIR/dir. We use sources argument
    # only to define explicit dependencies of the frozen C file
    frozen_action = \
        sbbs.verbosity.Action(
            get_tool_pathname(env, 'make-frozen.py') + ' %s > $TARGET' % dir[0],
                              "Processing frozen scripts in '%s': $TARGET" %
                              dir[0])
    sources = env.Glob(os.path.join(dir[0], '*.py'))
    frozen_scripts = env.Command(target,
                                 source=sources,
                                 action=frozen_action)


    return frozen_scripts
