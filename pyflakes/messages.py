# (c) 2005 Divmod, Inc.  See LICENSE file for details

class Message(object):
    message = ''
    level = 'N'

    def __init__(self, filename, loc, use_column=True, message_args=()):
        self.filename = filename
        self.lineno = loc.lineno
        self.col = getattr(loc, 'col_offset', None) if use_column else None
        self.message_args = message_args 

    def __str__(self):
        if self.col is not None:
            return '%s:%s(%d): [%s] %s' % (self.filename, self.lineno, self.col, self.level, self.message % self.message_args)
        else:
            return '%s:%s: [%s] %s' % (self.filename, self.lineno, self.level, self.message % self.message_args)

class Warning(Message):
    level = 'W'

class Error(Message):
    level = 'E'

class UnusedImport(Warning):
    message = '%r imported but unused'

    def __init__(self, filename, loc, name):
        Warning.__init__(self, filename, loc, use_column=False, message_args=(name,))
        self.name = name

class RedefinedWhileUnused(Warning):
    message = 'redefinition of unused %r from line %r'

    def __init__(self, filename, loc, name, orig_loc):
        Warning.__init__(self, filename, loc, message_args=(name, orig_loc.lineno))
        self.name = name
        self.orig_loc = orig_loc

class ImportShadowedByLoopVar(Warning):
    message = 'import %r from line %r shadowed by loop variable'

    def __init__(self, filename, loc, name, orig_loc):
        Warning.__init__(self, filename, loc, message_args=(name, orig_loc.lineno))
        self.name = name
        self.orig_loc = orig_loc

class ImportStarUsed(Warning):
    message = "'from %s import *' used; unable to detect undefined names"

    def __init__(self, filename, loc, modname):
        Warning.__init__(self, filename, loc, message_args=(modname,))
        self.name = modname

class UndefinedName(Error):
    message = 'undefined name %r'

    def __init__(self, filename, loc, name):
        Error.__init__(self, filename, loc, message_args=(name,))
        self.name = name

class UndefinedExport(Error):
    message = 'undefined name %r in __all__'

    def __init__(self, filename, loc, name):
        Error.__init__(self, filename, loc, message_args=(name,))
        self.name = name

class UndefinedLocal(Error):
    message = "local variable %r (defined in enclosing scope on line %r) referenced before assignment"

    def __init__(self, filename, loc, name, orig_loc):
        Error.__init__(self, filename, loc, message_args=(name, orig_loc.lineno))
        self.name = name
        self.orig_loc = orig_loc

class DuplicateArgument(Error):
    message = 'duplicate argument %r in function definition'

    def __init__(self, filename, loc, name):
        Error.__init__(self, filename, loc, message_args=(name,))
        self.name = name

class RedefinedFunction(Warning):
    message = 'redefinition of function %r from line %r'

    def __init__(self, filename, loc, name, orig_loc):
        Warning.__init__(self, filename, loc, message_args=(name, orig_loc.lineno))
        self.name = name
        self.orig_loc = orig_loc

class CouldNotCompile(Error):
    def __init__(self, filename, loc, msg=None, line=None):
        if msg and line:
            self.message = 'could not compile: %s\n%s'
            message_args = (msg, line)
        else:
            self.message = 'could not compile'
            message_args = ()
        Error.__init__(self, filename, loc, message_args=message_args)
        self.msg = msg
        self.line = line

class LateFutureImport(Warning):
    message = 'future import(s) %r after other statements'

    def __init__(self, filename, loc, names):
        Warning.__init__(self, filename, loc, message_args=(names,))
        self.names = names

class UnusedVariable(Warning):
    """
    Indicates that a variable has been explicity assigned to but not actually
    used.
    """

    message = 'local variable %r is assigned to but never used'

    def __init__(self, filename, loc, name):
        Warning.__init__(self, filename, loc, message_args=(name,))
        self.name = name
