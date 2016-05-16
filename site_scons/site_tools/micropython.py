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


def get_genhdr_pathname(env, header_name):
    """
    @return full pathname for a generated C-header file
    """
    return os.path.join(env.subst('#${VARIANT_DIR}'), 'genhdr',
                        header_name)


def get_script_pathname(env, script_name):
    """
    @return full pathname for helper script
    """
    return os.path.join('/usr', 'bin', 'python') + ' ' + \
        os.path.join(env.subst('${CONFIG.MICROPYTHON_DIR}'), 'py',
                     script_name)


def GenerateQstrDefs(env):
    preprocess_action = sbbs.verbosity.Action("cat $SOURCES | sed 's/^Q(.*)/\"&\"/' | $CPP $CFLAGS $_CCCOMCOM - | sed 's/^\"\(Q(.*)\)\"/\\1/' > $TARGET",
                                            'Preprocessing all qstrdefs headers, creating: $TARGET')
    preprocessed_header = \
        env.Command(get_genhdr_pathname(env, 'qstrdefs.preprocessed.h'),
                    [env.subst('${CONFIG.MICROPYTHON_DIR}/py/qstrdefs.h')]+
                    env['PY_QSTR_DEFS'],
                    action=preprocess_action,
                    source_scanner=SCons.Scanner.C.CScanner())

    generate_action = \
        sbbs.verbosity.Action(get_script_pathname(env,
                                                  'makeqstrdata.py') +
                              ' $SOURCE > $TARGET',
                              'Generating qstrdefs header: $TARGET')

    return env.Command(get_genhdr_pathname(env, 'qstrdefs.generated.h'),
                       preprocessed_header, action=generate_action)


def make_version(env):
    """
    Micropython version header generator
    """
    version_action = \
        sbbs.verbosity.Action(get_script_pathname(env, 'makeversionhdr.py') +
                              ' $TARGET',
                              'Generating Micropython version header: $TARGET')
    version_header = env.Command(get_genhdr_pathname(env, 'mpversion.h'),
                                 source=None,
                                 action=version_action)
    env.AlwaysBuild(version_header)


def generate(env):
    """Set build environment so that this project is also available to
    other projects
    """
    config = env['CONFIG']

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

    env.AddMethod(GenerateQstrDefs, 'GenerateQstrDefs')
    env.SetDefault(PY_QSTR_DEFS=[])
    make_version(env)

#    print env.Dump()

def exists(env):
    return 1
