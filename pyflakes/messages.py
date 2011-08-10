# (c) 2005 Divmod, Inc.  See LICENSE file for details

class Message(object):
    message = ''
    message_args = ()
    use_column = True
    names = ()

    def __init__(self, filename, source_node, *message_args):
        self.filename = filename
        self.lineno = source_node.lineno
        if self.use_column:
            self.col = getattr(source_node, 'col_offset', None)
        else:
            self.col = None
        self.message_args = message_args

    def __str__(self):
        return '%s:%s: %s' % (self.filename, self.lineno, self.message % self.message_args)


class UnusedImport(Message):
    message = '%r imported but unused'
    names = ('name',)
    use_column = False


class RedefinedWhileUnused(Message):
    message = 'redefinition of unused %r from line %r'
    names = 'name', 'orig_lineno'


class RedefinedInListComp(Message):
    message = 'list comprehension redefines %r from line %r'
    names = 'name', 'orig_lineno'


class ImportShadowedByLoopVar(Message):
    message = 'import %r from line %r shadowed by loop variable'
    names = 'name', 'orig_lineno'


class ImportStarUsed(Message):
    message = "'from %s import *' used; unable to detect undefined names"
    names = ('modname',)


class UndefinedName(Message):
    message = 'undefined name %r'
    names = ('name',)


class UndefinedExport(Message):
    message = 'undefined name %r in __all__'
    names = ('name',)


class UndefinedLocal(Message):
    message = "local variable %r (defined in enclosing scope on line %r) referenced before assignment"
    names = 'name', 'orig_lineno'


class DuplicateArgument(Message):
    message = 'duplicate argument %r in function definition'
    names = ('name',)


class RedefinedFunction(Message):
    message = 'redefinition of function %r from line %r'
    names = 'name', 'orig_lineno'


class LateFutureImport(Message):
    message = 'future import(s) %r after other statements'
    names = ('names',)


class UnusedVariable(Message):
    """
    Indicates that a variable has been explicity assigned to but not actually
    used.
    """

    message = 'local variable %r is assigned to but never used'
    names = ('names',)


class StringFormattingProblem(Message):
    message = 'string formatting arguments: should have %s, has %s'
    names = 'nshould', 'nhave'


class StringFormatProblem(Message):
    message = 'string.format(): %s'
    names = ('msg',)


class ExceptionReturn(Message):
    """
    Indicates that an Error or Exception is returned instead of raised.
    """

    message = 'exception %r is returned'
    names = ('name',)


class TupleCall(Message):
    """
    Indicates that an Error or Exception is returned instead of raised.
    """

    message = 'calling tuple literal, forgot a comma?'
