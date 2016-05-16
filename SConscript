Import('global_env')

# Qstrdefs
global_env.GenerateQstrDefs()

env = global_env.Clone()
Export('env')

# TODO: add debug variant
env.AppendUnique(CPPDEFINES=['NDEBUG'])
env.Replace(CCFLAGS_OPT='-Os')

env.FeatureSConscript(dirs=['py',
                            'extmod',
                            'lib',
                            'drivers'])

env.BuiltInObject(global_env)
