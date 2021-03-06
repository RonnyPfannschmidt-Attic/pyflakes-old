# -*- test-case-name: pyflakes -*-
# (c) 2005-2010 Divmod, Inc.
# See LICENSE file for details

import __builtin__
import os.path
import _ast
import re

from pyflakes import messages

interpol = re.compile(r'%(\([a-zA-Z0-9_]+\))?[-#0 +]*([0-9]+|[*])?'
                      r'(\.([0-9]+|[*]))?[hlL]?[diouxXeEfFgGcrs%]')

# utility function to iterate over an AST node's children, adapted
# from Python 2.6's standard ast module
try:
    import ast
    iter_child_nodes = ast.iter_child_nodes
except (ImportError, AttributeError):
    def iter_child_nodes(node, astcls=_ast.AST):
        """
        Yield all direct child nodes of *node*, that is, all fields that are nodes
        and all items of fields that are lists of nodes.
        """
        for name in node._fields:
            field = getattr(node, name, None)
            if isinstance(field, astcls):
                yield field
            elif isinstance(field, list):
                for item in field:
                    yield item


class Binding(object):
    """
    Represents the binding of a value to a name.

    The checker uses this to keep track of which names have been bound and
    which names have not. See L{Assignment} for a special type of binding that
    is checked with stricter rules.

    @ivar used: pair of (L{Scope}, line-number) indicating the scope and
                line number that this binding was last used
    """

    def __init__(self, name, source):
        self.name = name
        self.source = source
        self.used = False


    def __str__(self):
        return self.name


    def __repr__(self):
        return '<%s object %r from line %r at 0x%x>' % (self.__class__.__name__,
                                                        self.name,
                                                        self.source.lineno,
                                                        id(self))



class UnBinding(Binding):
    '''Created by the 'del' operator.'''



class Importation(Binding):
    """
    A binding created by an import statement.

    @ivar fullName: The complete name given to the import statement,
        possibly including multiple dotted components.
    @type fullName: C{str}
    """
    def __init__(self, name, source):
        self.fullName = name
        name = name.split('.')[0]
        super(Importation, self).__init__(name, source)



class Argument(Binding):
    """
    Represents binding a name as an argument.
    """



class Assignment(Binding):
    """
    Represents binding a name with an explicit assignment.

    The checker will raise warnings for any Assignment that isn't used. Also,
    the checker does not consider assignments in tuple/list unpacking to be
    Assignments, rather it treats them as simple Bindings.
    """



class FunctionDefinition(Binding):
    is_property = False



class ExportBinding(Binding):
    """
    A binding created by an C{__all__} assignment.  If the names in the list
    can be determined statically, they will be treated as names for export and
    additional checking applied to them.

    The only C{__all__} assignment that can be recognized is one which takes
    the value of a literal list containing literal strings.  For example::

        __all__ = ["foo", "bar"]

    Names which are imported and not otherwise used but appear in the value of
    C{__all__} will not have an unused import warning reported for them.
    """
    def names(self):
        """
        Return a list of the names referenced by this binding.
        """
        names = []
        if isinstance(self.source, (_ast.Tuple, _ast.List)):
            for node in self.source.elts:
                if isinstance(node, _ast.Str):
                    names.append(node.s)
        return names



class Scope(dict):
    importStarred = False       # set to True when import * is found


    def __repr__(self):
        return '<%s at 0x%x %s>' % (self.__class__.__name__, id(self), dict.__repr__(self))


    def __init__(self):
        super(Scope, self).__init__()

    def of_type(self, type):
        return isinstance(self, type)

class ClassScope(Scope):
    pass



class FunctionScope(Scope):
    """
    I represent a name scope for a function.

    @ivar globals: Names declared 'global' in this function.
    """
    def __init__(self):
        super(FunctionScope, self).__init__()
        self.globals = {}

class ConditionScope(Scope):
    #: set of the scope leaves and may be discarded for promotion
    escapes = False

    #XXX: maybe handle in the conditions
    def _get_import_starred(self):
        return self.parent.importStarred

    def _set_import_starred(self, value):
        self.parent.importStarred = value

    importStarred = property(_get_import_starred, _set_import_starred)

    def __init__(self, parent):
        super(ConditionScope, self).__init__()
        self.parent = parent

    def __getitem__(self, key):

        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.parent[key]

    @property
    def globals(self):
        return self.parent.globals


    def of_type(self, type):
        return self.parent.of_type(type) or isinstance(self, type)


class ModuleScope(Scope):
    pass


# Globally defined names which are not attributes of the __builtin__ module.
_MAGIC_GLOBALS = ['__file__', '__builtins__']



class Checker(object):
    """
    I check the cleanliness and sanity of Python code.

    @ivar _deferredFunctions: Tracking list used by L{deferFunction}.  Elements
        of the list are two-tuples.  The first element is the callable passed
        to L{deferFunction}.  The second element is a copy of the scope stack
        at the time L{deferFunction} was called.

    @ivar _deferredAssignments: Similar to C{_deferredFunctions}, but for
        callables which are deferred assignment checks.
    """

    nodeDepth = 0
    traceTree = False

    def __init__(self, tree, filename='(none)', traceTree=False):
        self._deferredFunctions = []
        self._deferredAssignments = []
        self.dead_scopes = []
        self.messages = []
        self.filename = filename
        self.scopeStack = [ModuleScope()]
        self.traceTree = traceTree
        self.futuresAllowed = True
        self.handleChildren(tree)
        self._runDeferred(self._deferredFunctions)
        # Set _deferredFunctions to None so that deferFunction will fail
        # noisily if called after we've run through the deferred functions.
        self._deferredFunctions = None
        self._runDeferred(self._deferredAssignments)
        # Set _deferredAssignments to None so that deferAssignment will fail
        # noisly if called after we've run through the deferred assignments.
        self._deferredAssignments = None
        del self.scopeStack[1:]
        self.popScope()
        self.check_dead_scopes()


    def deferFunction(self, callable):
        '''
        Schedule a function handler to be called just before completion.

        This is used for handling function bodies, which must be deferred
        because code later in the file might modify the global scope. When
        `callable` is called, the scope at the time this is called will be
        restored, however it will contain any new bindings added to it.
        '''
        self._deferredFunctions.append((callable, self.scopeStack[:]))


    def deferAssignment(self, callable):
        """
        Schedule an assignment handler to be called just after deferred
        function handlers.
        """
        self._deferredAssignments.append((callable, self.scopeStack[:]))


    def _runDeferred(self, deferred):
        """
        Run the callables in C{deferred} using their associated scope stack.
        """
        for handler, scope in deferred:
            self.scopeStack = scope
            handler()


    def scope(self):
        return self.scopeStack[-1]
    scope = property(scope)

    def popScope(self):
        scope = self.scopeStack.pop()
        # dirty hack
        if isinstance(scope, ConditionScope):
            self.scopeStack.append(scope.parent)
        self.dead_scopes.append(scope)
        return scope


    def check_dead_scopes(self):
        """
        Look at scopes which have been fully examined and report names in them
        which were imported but unused.
        """
        for scope in self.dead_scopes:
            export = isinstance(scope.get('__all__'), ExportBinding)
            if export:
                all = scope['__all__'].names()
                if os.path.split(self.filename)[1] != '__init__.py':
                    # Look for possible mistakes in the export list
                    undefined = set(all) - set(scope)
                    for name in undefined:
                        self.report(
                            messages.UndefinedExport,
                            scope['__all__'].source,
                            name)
            else:
                all = []

            # Look for imported names that aren't used.
            for importation in scope.itervalues():
                if isinstance(importation, Importation):
                    if not importation.used and importation.name not in all:
                        self.report(
                            messages.UnusedImport,
                            importation.source,
                            importation.name)


    def pushFunctionScope(self):
        self.scopeStack.append(FunctionScope())

    def pushClassScope(self):
        self.scopeStack.append(ClassScope())

    def pushConditionScope(self):
        #XXX:hack
        self.scopeStack[-1] = ConditionScope(self.scope)

    def report(self, messageClass, *args, **kwargs):
        msg = messageClass(self.filename, *args, **kwargs)
        self.messages.append(msg)

    def handleChildren(self, tree):
        for node in iter_child_nodes(tree):
            self.handleNode(node, tree)

    def isDocstring(self, node):
        """
        Determine if the given node is a docstring, as long as it is at the
        correct place in the node tree.
        """
        return isinstance(node, _ast.Str) or \
               (isinstance(node, _ast.Expr) and
                isinstance(node.value, _ast.Str))

    def handleNode(self, node, parent):
        node.parent = parent
        if self.traceTree:
            print '  ' * self.nodeDepth + node.__class__.__name__
        self.nodeDepth += 1
        if self.futuresAllowed and not \
               (isinstance(node, _ast.ImportFrom) or self.isDocstring(node)):
            self.futuresAllowed = False
        nodeType = node.__class__.__name__.upper()
        try:
            handler = getattr(self, nodeType)
            handler(node)
        finally:
            self.nodeDepth -= 1
        if self.traceTree:
            print '  ' * self.nodeDepth + 'end ' + node.__class__.__name__

    def ignore(self, node):
        pass

    # "stmt" type nodes
    DELETE = PRINT = WHILE = WITH = \
        TRYFINALLY = ASSERT = EXEC = EXPR = handleChildren

    CONTINUE = BREAK = PASS = ignore

    # "expr" type nodes
    BOOLOP = UNARYOP = IFEXP = DICT = SET = YIELD = COMPARE = \
        REPR = SUBSCRIPT = LIST = TUPLE = handleChildren

    NUM = STR = ELLIPSIS = ignore

    # "slice" type nodes
    SLICE = EXTSLICE = INDEX = handleChildren

    # expression contexts are node instances too, though being constants
    LOAD = STORE = DEL = AUGLOAD = AUGSTORE = PARAM = ignore

    # same for operators
    AND = OR = ADD = SUB = MULT = DIV = MOD = POW = LSHIFT = RSHIFT = \
    BITOR = BITXOR = BITAND = FLOORDIV = INVERT = NOT = UADD = USUB = \
    EQ = NOTEQ = LT = LTE = GT = GTE = IS = ISNOT = IN = NOTIN = ignore

    # additional node types
    COMPREHENSION = EXCEPTHANDLER = KEYWORD = handleChildren

    def hasParent(self, node, kind):
        parent = getattr(node, 'parent', None)
        while True:
            if not parent:
                return False
            elif isinstance(parent, kind):
                return True
            parent = getattr(parent, 'parent', None)

    def addBinding(self, node, value, reportRedef=True):
        '''Called when a binding is altered.

        - `lineno` is the line of the statement responsible for the change
        - `value` is the optional new value, a Binding instance, associated
          with the binding; if None, the binding is deleted if it exists.
        - if `reportRedef` is True (default), rebinding while unused will be
          reported.
        '''
        if (isinstance(self.scope.get(value.name), FunctionDefinition)
                    and isinstance(value, FunctionDefinition)
                    and not self.scope.get(value.name).is_property
                    and not value.is_property):
            self.report(messages.RedefinedFunction,
                        node, value.name, self.scope[value.name].source.lineno)

        redefinedWhileUnused = False

        if not isinstance(self.scope, ClassScope):
            for scope in self.scopeStack[::-1]:
                existing = scope.get(value.name)
                if (isinstance(existing, Importation)
                        and not existing.used
                        and (not isinstance(value, Importation) or value.fullName == existing.fullName)
                        and reportRedef):
                    redefinedWhileUnused = True

                    self.report(messages.RedefinedWhileUnused,
                                node, value.name, scope[value.name].source.lineno)

        if (not redefinedWhileUnused and
            self.hasParent(value.source, _ast.ListComp)):
            existing = self.scope.get(value.name)
            if (existing and
                not self.hasParent(existing.source, (_ast.For, _ast.ListComp))
                and reportRedef):
                self.report(messages.RedefinedInListComp, node, value.name,
                            self.scope[value.name].source.lineno)

        if isinstance(value, UnBinding):
            try:
                self.scope[value.name]
                if self.scope.pop(value.name, None) is None:
                    #XXX: del in condition scope
                    pass
            except KeyError:
                self.report(messages.UndefinedName, node, value.name)
        else:
            self.scope[value.name] = value

    def GLOBAL(self, node):
        """
        Keep track of globals declarations.
        """
        if isinstance(self.scope, FunctionScope):
            self.scope.globals.update(dict.fromkeys(node.names))

    def LISTCOMP(self, node):
        # handle generators before element
        for gen in node.generators:
            self.handleNode(gen, node)
        self.handleNode(node.elt, node)

    GENERATOREXP = SETCOMP = LISTCOMP

    # dictionary comprehensions; introduced in Python 2.7
    def DICTCOMP(self, node):
        for gen in node.generators:
            self.handleNode(gen, node)
        self.handleNode(node.key, node)
        self.handleNode(node.value, node)

    def FOR(self, node):
        """
        Process bindings for loop variables.
        """
        vars = []
        def collectLoopVars(n):
            if isinstance(n, _ast.Name):
                vars.append(n.id)
            elif isinstance(n, _ast.expr_context):
                return
            else:
                for c in iter_child_nodes(n):
                    collectLoopVars(c)

        collectLoopVars(node.target)
        for varn in vars:
            if (isinstance(self.scope.get(varn), Importation)
                    # unused ones will get an unused import warning
                    and self.scope[varn].used):
                self.report(messages.ImportShadowedByLoopVar,
                            node, varn, self.scope[varn].source.lineno)

        self.handleChildren(node)

    def BINOP(self, node):
        if isinstance(node.op, _ast.Mod) and isinstance(node.left, _ast.Str):
            dictfmt = ('%(' in node.left.s and '%%(' not in node.left.s)
            nplaces = 0
            for m in interpol.finditer(node.left.s):
                if m.group()[-1] != '%':
                    nplaces += 1 + m.group().count('*')
            if isinstance(node.right, _ast.Dict):
                if not dictfmt:
                    self.report(messages.StringFormattingProblem,
                                node, 'tuple', 'dict')
            else:
                if isinstance(node.right, _ast.Tuple):
                    if dictfmt:
                        self.report(messages.StringFormattingProblem,
                                    node, 'dict', 'tuple')
                    else:
                        nobjects = len(node.right.elts)
                        if nobjects != nplaces:
                            self.report(messages.StringFormattingProblem,
                                        node, nplaces, nobjects)
            self.handleNode(node.right, node)
        else:
            self.handleNode(node.left, node)
            self.handleNode(node.right, node)

    def CALL(self, node):
        if isinstance(node.func, _ast.Tuple):
            self.report(messages.TupleCall, node)
        self.handleChildren(node)

    def ATTRIBUTE(self, node):
        if isinstance(node.value, _ast.Str) and node.attr == 'format' and \
           isinstance(node.parent, _ast.Call) and node is node.parent.func:
            try:
                num = 0
                maxnum = -1
                kwds = set()
                for lit, fn, fs, conv in node.value.s._formatter_parser():
                    if lit:
                        continue
                    fn = fn.partition('.')[0].partition('[')[0]
                    if not fn:
                        num += 1
                    elif fn.isdigit():
                        maxnum = max(maxnum, int(fn))
                    else:
                        kwds.add(fn)
            except ValueError, err:
                self.report(messages.StringFormatProblem,
                            node, str(err))
            else:
                callnode = node.parent
                # can only really check if no *args or **kwds are used
                if not (callnode.starargs or callnode.kwargs):
                    nargs = len(node.parent.args)
                    kwdset = set(kwd.arg for kwd in node.parent.keywords)
                    if nargs < num:
                        self.report(messages.StringFormatProblem, node,
                                    'not enough positional args (need %s)' % num)
                    elif nargs < maxnum+1:
                        self.report(messages.StringFormatProblem, node,
                                    'not enough positional args (need %s)' %
                                    (maxnum+1))
                    missing = kwds - kwdset
                    if missing:
                        self.report(messages.StringFormatProblem, node,
                                    'keyword args missing: %s' % ', '.join(missing))
        else:
            self.handleNode(node.value, node)

    def NAME(self, node):
        """
        Handle occurrence of Name (which can be a load/store/delete access.)
        """
        # Locate the name in locals / function / globals scopes.
        if isinstance(node.ctx, (_ast.Load, _ast.AugLoad)):
            # try local scope
            importStarred = self.scope.importStarred
            try:
                self.scope[node.id].used = (self.scope, node)
            except KeyError:
                pass
            else:
                return

            # try enclosing function scopes

            for scope in self.scopeStack[-2:0:-1]:
                importStarred = importStarred or scope.importStarred
                if not scope.of_type(FunctionScope):
                    continue
                try:
                    scope[node.id].used = (self.scope, node)
                except KeyError:
                    pass
                else:
                    return

            # try global scope

            importStarred = importStarred or self.scopeStack[0].importStarred
            try:
                self.scopeStack[0][node.id].used = (self.scope, node)
            except KeyError:
                if ((not hasattr(__builtin__, node.id))
                        and node.id not in _MAGIC_GLOBALS
                        and not importStarred):
                    if (os.path.basename(self.filename) == '__init__.py' and
                        node.id == '__path__'):
                        # the special name __path__ is valid only in packages
                        pass
                    else:
                        self.report(messages.UndefinedName, node, node.id)
        elif isinstance(node.ctx, (_ast.Store, _ast.AugStore)):
            # if the name hasn't already been defined in the current scope
            if isinstance(self.scope, FunctionScope) and node.id not in self.scope:
                # for each function or module scope above us
                for scope in self.scopeStack[:-1]:
                    if not isinstance(scope, (FunctionScope, ModuleScope)):
                        continue
                    # if the name was defined in that scope, and the name has
                    # been accessed already in the current scope, and hasn't
                    # been declared global
                    if (node.id in scope
                            and scope[node.id].used
                            and scope[node.id].used[0] is self.scope
                            and node.id not in self.scope.globals):
                        # then it's probably a mistake
                        self.report(messages.UndefinedLocal,
                                    scope[node.id].used[1],
                                    node.id,
                                    scope[node.id].source.lineno)
                                    # kevins fork used the source info instead of lineno here,
                                    # however the message ctor did just revert that
                        break

            if isinstance(node.parent,
                          (_ast.For, _ast.comprehension, _ast.Tuple, _ast.List)):
                binding = Binding(node.id, node)
            elif (node.id == '__all__' and
                  isinstance(self.scope, ModuleScope)):
                binding = ExportBinding(node.id, node.parent.value)
            else:
                binding = Assignment(node.id, node)
            if node.id in self.scope:
                binding.used = self.scope[node.id].used
            self.addBinding(node, binding)
        elif isinstance(node.ctx, _ast.Del):
            if isinstance(self.scope, FunctionScope) and \
                   node.id in self.scope.globals:
                del self.scope.globals[node.id]
            else:
                self.addBinding(node, UnBinding(node.id, node))
        else:
            # must be a Param context -- this only happens for names in function
            # arguments, but these aren't dispatched through here
            raise RuntimeError(
                "Got impossible expression context: %r" % (node.ctx,))


    def FUNCTIONDEF(self, node):
        # the decorators attribute is called decorator_list as of Python 2.6
        is_property = False
        if hasattr(node, 'decorators'):
            decorators = node.decorators
        else:
            decorators = node.decorator_list

        for deco in decorators:
            self.handleNode(deco, node)
            if getattr(deco, 'id', None) == 'property':
                is_property = True
            if getattr(deco, 'attr', None) in ('setter', 'deleter'):
                is_property = True

        funcdef = FunctionDefinition(node.name, node)
        funcdef.is_property = is_property
        self.addBinding(node, funcdef)
        self.LAMBDA(node)

    def LAMBDA(self, node):
        for default in node.args.defaults:
            self.handleNode(default, node)

        def runFunction():
            args = []

            def addArgs(arglist):
                for arg in arglist:
                    if isinstance(arg, _ast.Tuple):
                        addArgs(arg.elts)
                    else:
                        if arg.id in args:
                            self.report(messages.DuplicateArgument, node, arg.id)
                        args.append(arg.id)

            self.pushFunctionScope()
            addArgs(node.args.args)
            # vararg/kwarg identifiers are not Name nodes
            if node.args.vararg:
                args.append(node.args.vararg)
            if node.args.kwarg:
                args.append(node.args.kwarg)
            for name in args:
                self.addBinding(node, Argument(name, node), reportRedef=False)
            if isinstance(node.body, list):
                # case for FunctionDefs
                for stmt in node.body:
                    self.handleNode(stmt, node)
            else:
                # case for Lambdas
                self.handleNode(node.body, node)
            def checkUnusedAssignments():
                """
                Check to see if any assignments have not been used.
                """
                for name, binding in self.scope.iteritems():
                    if name == '__tracebackhide__':
                        # used to hide frames in pytest
                        continue
                    if (not binding.used and not name in self.scope.globals
                        and isinstance(binding, Assignment)):
                        self.report(messages.UnusedVariable,
                                    binding.source, name)
            self.deferAssignment(checkUnusedAssignments)
            self.popScope()

        self.deferFunction(runFunction)


    def CLASSDEF(self, node):
        """
        Check names used in a class definition, including its decorators, base
        classes, and the body of its definition.  Additionally, add its name to
        the current scope.
        """
        # decorator_list is present as of Python 2.6
        for deco in getattr(node, 'decorator_list', []):
            self.handleNode(deco, node)
        for baseNode in node.bases:
            self.handleNode(baseNode, node)
        self.pushClassScope()
        for stmt in node.body:
            self.handleNode(stmt, node)
        self.popScope()
        self.addBinding(node, Binding(node.name, node))

    def ASSIGN(self, node):
        self.handleNode(node.value, node)
        for target in node.targets:
            self.handleNode(target, node)

    def AUGASSIGN(self, node):
        # AugAssign is awkward: must set the context explicitly and visit twice,
        # once with AugLoad context, once with AugStore context
        node.target.ctx = _ast.AugLoad()
        self.handleNode(node.target, node)
        self.handleNode(node.value, node)
        node.target.ctx = _ast.AugStore()
        self.handleNode(node.target, node)

    def IMPORT(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            importation = Importation(name, node)
            self.addBinding(node, importation)

    def IMPORTFROM(self, node):
        if node.module == '__future__':
            if not self.futuresAllowed:
                self.report(messages.LateFutureImport, node,
                            [n.name for n in node.names])
        else:
            self.futuresAllowed = False

        for alias in node.names:
            if alias.name == '*':
                self.scope.importStarred = True
                self.report(messages.ImportStarUsed, node, node.module)
                continue
            name = alias.asname or alias.name
            importation = Importation(name, node)
            if node.module == '__future__':
                importation.used = (self.scope, node)
            self.addBinding(node, importation)

    def RETURN(self, node):
        self.scope.escapes = True
        if not node.value:
            return
        self.handleNode(node.value, node)
        if isinstance(node.value, _ast.Name):
            name = node.value.id
        elif isinstance(node.value, _ast.Call) and \
           isinstance(node.value.func, _ast.Name):
            name = node.value.func.id
        else:
            return
        if name.endswith('Error') or name.endswith('Exception'):
            self.report(messages.ExceptionReturn, node, name)

    def TRYEXCEPT(self, node):
        """
        Handle C{try}-C{except}.  In particular, do not report redefinitions
        when occurring in an "except ImportError" block.
        """
        self.pushConditionScope()
        for stmt in node.body:
            self.handleNode(stmt, node)
        body_scope = self.popScope()

        handler_scopes = [body_scope]
        for handler in node.handlers:
            if handler.type:
                self.handleNode(handler.type, node)
                if handler.name:
                    self.handleNode(handler.name, node)
            self.pushConditionScope()
            for stmt in handler.body:
                self.handleNode(stmt, node)
            handler_scopes.append(self.popScope())

        #XXX complicated logic, check
        valid_scopes = [scope for scope in handler_scopes if not scope.escapes]
        if valid_scopes:
            common = set(valid_scopes[0])
            for scope in valid_scopes[1:]:
                common.intersection_update(scope)
            # when the body scope doesnt raise,
            # its currently the best to consider its names
            # availiable for the orelse part
            if not body_scope.escapes:
                common.update(body_scope)

            for name in common:
                #XXX: really ok?
                self.scope[name] = valid_scopes[0].pop(name)
                for scope in valid_scopes[1:]:
                    scope.pop(name, None) # might not exist when body is ok

        for scope in valid_scopes:
            for key, binding in scope.items():
                if key not in self.scope and not binding.used:
                    # bubble up all unused variables
                    # this should rather use the possible flowgraphs
                    self.scope[key] = binding


        for stmt in node.orelse:
            self.handleNode(stmt, node)

    def RAISE(self, node):
        """
        mark a scope if a exception is raised in it
        """
        self.scope.escapes = True
        self.handleChildren(node)


    def IF(self, node):
        """
        handle if statements,
        use subscopes, and reconcile them in the parent scope
        special conditions for raising
        """

        self.handleNode(node.test, node)

        # special case to handle modules with execnet channels
        if isinstance(self.scope, ModuleScope) \
           and isinstance(node.test, _ast.Compare) \
           and len(node.test.ops) == 1 \
           and isinstance(node.test.ops[0], _ast.Eq) \
           and isinstance(node.test.left, _ast.Name) \
           and node.test.left.id == '__name__' \
           and isinstance(node.test.comparators[0], _ast.Str) \
           and node.test.comparators[0].s == '__channelexec__':
            #XXX: is that semantically valid?
            self.addBinding(node, Binding('channel', node))


        self.pushConditionScope()
        for stmt in node.body:
            self.handleNode(stmt, node)
        body_scope = self.popScope()

        self.pushConditionScope()
        for stmt in node.orelse:
            self.handleNode(stmt, node)
        else_scope = self.popScope()

        if body_scope.escapes and else_scope.escapes:
            pass
        elif body_scope.escapes:
            self.scope.update(else_scope)
        elif else_scope.escapes:
            self.scope.update(body_scope)
        else:
            #XXX: better scheme for unsure bindings
            common = set(body_scope) & set(else_scope)
            for key in common:
                self.scope[key] = body_scope[key]

            for key, binding in body_scope.items():
                if key not in self.scope and not binding.used:
                    #XXX: wrap it?
                    self.scope[key] = binding

            for key, binding in else_scope.items():
                if key not in self.scope and not binding.used:
                    #XXX: wrap it?
                    self.scope[key] = binding



