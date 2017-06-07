"""This module provides functionality for extracting Qstr definitions
   from sources and generating the top level qstr definitions header
   (qstrdefs.generated.h)

   Copyright (c) 2016 Braiins Systems s.r.o.
"""
import os
import sys

import pila.verbosity
import SCons.Scanner

import makeqstrdata
import micropython.makeqstrdefs
from micropython.utils import get_genhdr_pathname, get_script_pathname

class QstrCScanner(SCons.Scanner.ClassicCPP):
    """
    Special C file scanner that filters the generated list of nodes
    are removes the qstrdefs.generated.h
    """
    def __init__(self, qstrdefs_header):
        self.qstrdefs_header = qstrdefs_header
        super(SCons.Scanner.ClassicCPP, self).__init__('CScanner',
                                                       '$CPPSUFFIXES',
                                                       'CPPPATH',
                                                       '^[ \t]*#[ \t]*(?:include|import)[ \t]*(<|")([^>"]+)(>|")')


    def scan(self, node, path=()):
        nodes = super(SCons.Scanner.ClassicCPP, self).scan(node, path)
        filtered_nodes = \
            [node for node in nodes if node.abspath != self.qstrdefs_header.abspath]

        return filtered_nodes


class QstrDefsMgr(object):
    """
    This class provides all functionality required for handling
    qstrdefs generation.
    """
    def __init__(self, env):
        self.env = env
        # Final generated file
        self.qstrdefs_generated_h = env.File(get_genhdr_pathname(env,
                                                            'qstrdefs.generated.h'))
        # Intermediate qstrdefs file
        self.qstrdefs_preprocessed_h = get_genhdr_pathname(env,
                                                           'qstrdefs.preprocessed.h')
        self.qstr_c_scanner = QstrCScanner(self.qstrdefs_generated_h)



def qstrdefs_mgr(env):
    return env['MICROPYTHON_QSTRDEFS_MGR']


def generate(env):
    """
    Updates construction environment for qstring generation
    """
    env.AddMethod(QstrHeader, 'QstrHeader')
    env.AddMethod(QstrFeatureObject, 'QstrFeatureObject')

    env.AddMethod(GenerateQstrDefs, 'GenerateQstrDefs')
    env.SetDefault(PY_QSTR_DEFS=[])
    # Storage for the collected (auto generated qstrdefs files)
    env.SetDefault(PY_QSTR_DEFS_COLLECTED=[])

    # Append the qstrings manager
    env.Append(MICROPYTHON_QSTRDEFS_MGR=QstrDefsMgr(env))


def make_qstr_data(env, target, source):
    """
    Creates qstr data header from the specified sources + all the
    collected qstr files.
    """
    # makeqstrdata.py sends all results to stdout. Therefore, we
    # temporarily redirect it to generate the complete qstrdefs header
    # NOTE: the collected qstrdefs are being append as last into the
    # list of input files. This is to make qstrdefs, that have been
    # manually defined, have higher priority while generating this
    # header.
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
    preprocess_action = pila.verbosity.Action("cat $SOURCES $PY_QSTR_DEFS | sed 's/^Q(.*)/\"&\"/' | $CPP $CFLAGS $_CCCOMCOM - | sed 's/^\"\(Q(.*)\)\"/\\1/' > $TARGET",
                                            'Preprocessing all qstrdefs headers, creating: $TARGET')

    preprocessed_header = \
        env.Command(qstrdefs_mgr(env).qstrdefs_preprocessed_h,
                    [env.subst('${CONFIG.MICROPYTHON_DIR}/py/qstrdefs.h')],
                    action=preprocess_action,
                    source_scanner=SCons.Scanner.C.CScanner())

    generate_action = \
        pila.verbosity.Action(make_qstr_data,
                              'Generating qstrdefs header: $TARGET')

    return env.Command(qstrdefs_mgr(env).qstrdefs_generated_h,
                       preprocessed_header, action=generate_action)


def create_qstr_file(env, target, source):
    """
    Creates a qstr file from a preprocessed source
    """
    with open(str(source[0]), 'r') as source_file:
        qstr_data = micropython.makeqstrdefs.process_file(source_file)
        with open(str(target[0]), 'w') as qstr_file:
            qstr_file.write(qstr_data)


def qstr_file(env, target, source, depends):
    """
    A pseudo builder that generates a .qstr file. Each file is being
    preprocessed first and then it is being run through a qstr
    extractor.
    """
    # C-preprocessor action for the source
    preprocess_action = \
        pila.verbosity.Action('$CPP $CFLAGS $CCFLAGS $_CCCOMCOM $SOURCES -o $TARGET',
                              '[CPP-QSTR]: $TARGET')

    # Actual qstr extraction action
    gen_action = pila.verbosity.Action(create_qstr_file,
                                       '[MAKEQSTR]: $TARGET')


    if not SCons.Util.is_List(source):
        source = [source]

    qstr_files = []
    for s in source:
        if target is None:
            real_target = s
        else:
            real_target = target

        preprocessed_file = env.Command('%s.qstr.i' % real_target, s,
                                        action=preprocess_action,
                                        CPPDEFINES=['$CPPDEFINES',
                                                    '__QSTR_EXTRACT'],
                                        source_scanner=qstrdefs_mgr(env).qstr_c_scanner)

        # Add explicit dependencies
        env.Depends(preprocessed_file, depends)

        # Command result is only 1 target, therefore we extract the
        # only element of the list
        qstr_files.append(env.Command('%s.qstr' % real_target, preprocessed_file,
                                      action=gen_action)[0])

    return qstr_files


def QstrHeader(env, source):
    """
    Pseudo builder that declares and registers sources among qstring
    definition headers and extends the dependency preprocessed output
    of these.
    """
    if not SCons.Util.is_List(source):
        source = [source]
    env['PY_GLOBAL_ENV'].Append(PY_QSTR_DEFS=map(env.GetBuildPath, source))
    env['PY_GLOBAL_ENV'].Depends(qstrdefs_mgr(env).qstrdefs_preprocessed_h,
                                 source)


def QstrFeatureObject(env, target=None, source=None, *args, **kw):
    """
    A pseudo builder for a feature object with qstrings extractor.

    If the feature object is to be instantiated, it also provides a
    builder to extract qstrings from the source file and append the
    results to the collected header.
    """

    obj = env.FeatureObject(target, source, *args, **kw)
    if obj is not None:
        # All explicit dependencies of feature object are transitioned to
        # the qstr file, too. See qstr_file() for details
        generated_qstr_file = qstr_file(env, target, source,
                                        depends=obj[0].depends)
        env['PY_GLOBAL_ENV'].Append(PY_QSTR_DEFS_COLLECTED=generated_qstr_file)
        # Each .qstr generated file adds to the dependencies of the top
        # main qstrdefs generated header
        env['PY_GLOBAL_ENV'].Depends(qstrdefs_mgr(env).qstrdefs_generated_h,
                                     generated_qstr_file)

    return obj
