"""This module provides functionality for extracting Qstr definitions
   from sources and generating the top level qstr definitions header
   (qstrdefs.generated.h)

   Copyright (c) 2016 Braiins Systems s.r.o.
"""
import os
import sys

import sbbs.verbosity
import SCons.Scanner

import makeqstrdata
import micropython.makeqstrdefs
from micropython.utils import get_genhdr_pathname, get_script_pathname


def make_qstr_data(env, target, source):
    """
    Creates qstr data header from the specified sources + all the
    collected qstr files.
    """
    # makeqstrdata.py sends all results to stdout. Therefore, we
    # temporarily redirect it to generate the complete qstrdefs header
    # NOTE: the collected qstrdefs are being append as last so that
    # qstrdefs, that has been manually defined, have higher priority
    # while generating this
    infiles = map(str,
                  source + env['PY_GLOBAL_ENV']['PY_QSTR_DEFS_COLLECTED'])

    old_stdout = sys.stdout
    with open(str(target[0]), 'w') as target_file:
        sys.stdout = target_file
        makeqstrdata.do_work(infiles)

    sys.stdout = old_stdout


def GenerateQstrDefs(env):
    """
    Generates qstrdefs.generated.h header that contains all qstrings
    collected from all associated projects.
    """

    # Qstr definitions are being protected from the preprocessor by
    # wrapping the lines in "" and then unwrapping them after the
    # preprocessor has finished
    preprocess_action = sbbs.verbosity.Action("cat $SOURCES $PY_QSTR_DEFS | sed 's/^Q(.*)/\"&\"/' | $CPP $CFLAGS $_CCCOMCOM - | sed 's/^\"\(Q(.*)\)\"/\\1/' > $TARGET",
                                            'Preprocessing all qstrdefs headers, creating: $TARGET')

    preprocessed_header = \
        env.Command(get_genhdr_pathname(env,
                                        'qstrdefs.preprocessed.h'),
                    [env.subst('${CONFIG.MICROPYTHON_DIR}/py/qstrdefs.h')],
                    action=preprocess_action,
                    source_scanner=SCons.Scanner.C.CScanner())

    generate_action = \
        sbbs.verbosity.Action(make_qstr_data,
                              'Generating qstrdefs header: $TARGET')

    return env.Command(get_genhdr_pathname(env, 'qstrdefs.generated.h'),
                       preprocessed_header, action=generate_action)


def create_qstr_file(env, target, source):
    """
    Creates a qstr file from a preprocessed source
    """
    with open(str(source[0]), 'r') as source_file:
        qstr_data = micropython.makeqstrdefs.process_file(source_file)
        with open(str(target[0]), 'w') as qstr_file:
            qstr_file.write(qstr_data)


def qstr_file(env, source):
    """
    A pseudo builder that generates a .qstr file. Each file is being
    preprocessed first and then it is being run through a qstr
    extractor.
    """
    # C-preprocessor action for the source
    preprocess_action = \
        sbbs.verbosity.Action('$CPP $CFLAGS $CCFLAGS $_CCCOMCOM $SOURCES -o $TARGET',
                              '[CPP-QSTR]: $TARGET')

    # Actual qstr extraction action
    gen_action = sbbs.verbosity.Action(create_qstr_file,
                                       '[MAKEQSTR]: $TARGET')

    if not SCons.Util.is_List(source):
        source = [source]

    qstr_files = []
    for s in source:
        preprocessed_file = env.Command('%s.qstr.i' % s, s,
                                        action=preprocess_action,
                                        CPPDEFINES=['$CPPDEFINES',
                                                    '__QSTR_EXTRACT'])
        # Commands result is only 1 target, there we extract the only
        # element of the list
        qstr_files.append(env.Command('%s.qstr' % s, preprocessed_file,
                                      action=gen_action)[0])

    return qstr_files


def QstrHeader(env, source):
    """
    Pseudo builder that declares a registers sources among qstring
    definition headers and extends the dependency preprocessed output
    of these.
    """
    if not SCons.Util.is_List(source):
        source = [source]
    env['PY_GLOBAL_ENV'].Append(PY_QSTR_DEFS=map(env.GetBuildPath, source))
    env['PY_GLOBAL_ENV'].Depends(get_genhdr_pathname(env,
                                                     'qstrdefs.preprocessed.h'),
                                 source)


def QstrFeatureObject(env, target=None, source=None, *args, **kw):
    """
    A pseudo builder that declares a feature object. If the feature
    object is to be instantiated, it also provides a builder to
    extract qstrings from the source file and append the results to
    the collected header.
    """

    obj = env.FeatureObject(target, source, *args, **kw)

    if obj is not None:
        generated_qstr_file = qstr_file(env, source=source)
        env['PY_GLOBAL_ENV'].Append(PY_QSTR_DEFS_COLLECTED=generated_qstr_file)
        # Each .qstr generated file adds to the dependencies of the top
        # main qstrdefs generated header
        env['PY_GLOBAL_ENV'].Depends(get_genhdr_pathname(env,
                                                         'qstrdefs.generated.h'),
                                     generated_qstr_file)
