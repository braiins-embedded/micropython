"""Scons Tool for building external sources against micropython.
   The tool assumes the build configuration is available through
   construction environment variable 'CONFIG'. The following
   configuration elements are required:

   - MICROPYTHON_DIR - top level directory that contains the source
     tree

   Copyright (c) 2016 Braiins Systems s.r.o.
"""
import os
import sbbs.verbosity
import SCons.Scanner
import micropython.utils
import sys

from micropython.utils import get_genhdr_pathname, get_script_pathname
import micropython.frozen


def make_version(env):
    """
    Micropython version header generator
    """
    version_action = \
        sbbs.verbosity.Action(get_script_pathname(env,
                                                  'makeversionhdr.py') +
                              ' $TARGET',
                              'Generating Micropython version header: $TARGET')
    version_header = env.Command(get_genhdr_pathname(env,
                                                     'mpversion.h'),
                                 source=None,
                                 action=version_action)
    env.AlwaysBuild(version_header)


def generate(env):
    """Set build environment so that this project is also available to
    other projects
    """
    config = env['CONFIG']

    # modify python path, so that we can access micropython's build
    # scripts
    sys.path.append(os.path.join(config.MICROPYTHON_DIR, 'py'))


    lib_path = 'lib'
    mp_readline_path = os.path.join(lib_path, 'mp-readline')
    netutils_path = os.path.join(lib_path, 'netutils')
    timeutils_path = os.path.join(lib_path, 'timeutils')

    cpp_path = [os.path.join(config.MICROPYTHON_DIR, path) for path in
                [mp_readline_path, netutils_path, timeutils_path]]

    env.Append(CPPPATH = [config.MICROPYTHON_DIR] + cpp_path)

    env.AppendUnique(CFLAGS=['-ansi', '-std=gnu99'])
    # TODO: add debug variant
    env.AppendUnique(CPPDEFINES=['NDEBUG'])

    # TODO: importing qstrdefs module requires sys.path pointing to py/
    # directory for makeqstrdata -> mov this up etc.
    import micropython.qstrdefs
    micropython.qstrdefs.generate(env)

    micropython.frozen.generate(env)

    env.Append(PY_GLOBAL_ENV=env)

    make_version(env)

    print env.Dump()

def exists(env):
    return 1
