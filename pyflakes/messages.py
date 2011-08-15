# (c) 2005 Divmod, Inc.  See LICENSE file for details

class Message(object):
    message = ''
    message_args = ()
    use_column = True
    names = ()
    level = 'N'

    def __init__(self, filename, source_node, *message_args):
        self.filename = filename
        self.lineno = source_node.lineno
        if self.use_column:
            self.col = getattr(source_node, 'col_offset', None)
        else:
            self.col = None
        self.message_args = message_args

    def __str__(self):
        if self.col is not None:
            return '%s:%s(%d): [%s] %s' % (self.filename, self.lineno, self.col, self.level, self.message % self.message_args)
        elif self.lineno:
            return '%s:%s: [%s] %s' % (self.filename, self.lineno, self.level, self.message % self.message_args)
        else:
            return '%s: [%s] %s' % (self.filename, self.level, self.message % self.message_args)

class Warning(Message):
    level = 'W'

class Error(Message):
    level = 'E'

class UnusedImport(Warning):
    message = '%r imported but unused'
    names = ('name',)
    use_column = False


class RedefinedWhileUnused(Warning):
    message = 'redefinition of unused %r from line %r'
    names = 'name', 'orig_lineno'


class RedefinedInListComp(Warning):
    message = 'list comprehension redefines %r from line %r'
    names = 'name', 'orig_lineno'


class ImportShadowedByLoopVar(Warning):
    message = 'import %r from line %r shadowed by loop variable'
    names = 'name', 'orig_lineno'


class ImportStarUsed(Warning):
    message = "'from %s import *' used; unable to detect undefined names"
    names = ('modname',)


class UndefinedName(Error):
    message = 'undefined name %r'
    names = ('name',)


class UndefinedExport(Error):
    message = 'undefined name %r in __all__'
    names = ('name',)


class UndefinedExport(Error):
    message = 'undefined name %r in __all__'
    names = ('name',)
    

class UndefinedLocal(Error):
    message = "local variable %r (defined in enclosing scope on line %r) referenced before assignment"
    names = 'name', 'orig_lineno'


class DuplicateArgument(Error):
    message = 'duplicate argument %r in function definition'
    names = ('name',)


class RedefinedFunction(Warning):
    message = 'redefinition of function %r from line %r'
    names = 'name', 'orig_lineno'


class CouldNotCompile(Error):
    def __init__(self, filename, loc, msg=None, line=None):
        if not line:
            loc.lineno = None
        if msg and line:
            self.message = 'could not compile: %s\n%s'
            message_args = (msg, line)
        else:
            self.message = 'could not compile: %s'
            message_args = (msg,)
        Error.__init__(self, filename, loc, *message_args)
        self.loc = loc
        self.msg = msg
        self.line = line

    def __str__(self):
        err = Error.__str__(self)
        fname, line, pos, data = self.loc.args[1]
        if data:
            if '\n' not in data[:-1]:
                # weird single line error, like unexpected eof
                # the bool subtraction is to account for python2.7
                # adding a \n even if there is none in the source
                spaces = pos - (data[-1] == '\n') 
            else:
                spaces = pos - data.rfind('\n', 0, pos) -1
            return err + '\n%*.s' %(spaces, '') + '^'
        return err

class CouldNotLoad(Error):
    message = 'Could not load: %s'

    def __init__(self, filename, exc):
        exc.lineno = None
        Error.__init__(self, filename, exc, exc.args[1])


class LateFutureImport(Warning):
    message = 'future import(s) %r after other statements'
    names = ('names',)


class UnusedVariable(Warning):
    """
    Indicates that a variable has been explicity assigned to but not actually
    used.
    """

    message = 'local variable %r is assigned to but never used'
    names = ('names',)


class StringFormattingProblem(Warning):
    message = 'string formatting arguments: should have %s, has %s'
    names = 'nshould', 'nhave'


class StringFormatProblem(Warning):
    message = 'string.format(): %s'
    names = ('msg',)


class ExceptionReturn(Warning):
    """
    Indicates that an Error or Exception is returned instead of raised.
    """

    message = 'exception %r is returned'
    names = ('name',)


class TupleCall(Warning):
    """
    Indicates that a tuple is called (usually a forgotton collon in a list of tuples)
    """

    message = 'calling tuple literal, forgot a comma?'
    names = ('name',)
