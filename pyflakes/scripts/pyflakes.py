
"""
Implementation of the command-line I{pyflakes} tool.
"""

import _ast
import sys
import os
import optparse

checker = __import__('pyflakes.checker').checker

def check(codeString, filename, exclude=()):
    try:
        tree = compile(codeString, filename, 'exec', _ast.PyCF_ONLY_AST)
    except (SyntaxError, IndentationError):
        value = sys.exc_info()[1]
        try:
            (lineno, offset, line) = value[1][1:]
        except IndexError:
            print >> sys.stderr, 'could not compile %r' % (filename,)
            return 1
        if line.endswith("\n"):
            line = line[:-1]
        print >> sys.stderr, '%s:%d: could not compile' % (filename, lineno)
        print >> sys.stderr, line
        print >> sys.stderr, " " * (offset-2), "^"
        return 1
    else:
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        for warning in w.messages:
            if warning.level not in exclude:
                print warning
        return w.messages


def checkPath(filename, exclude=()):
    """
    Check the given path, printing out any warnings detected.

    @return: the number of warnings printed
    """
    if os.path.exists(filename):
        return check(file(filename, 'U').read() + '\n', filename, exclude)
    else:
        print >> sys.stderr, '%s: no such file' % (filename,)
        return 1

def main():
    parser = optparse.OptionParser(usage='usage: %prog [options] module')
    parser.add_option('-x', '--exclude', action='append', dest='exclude', help='exclude levels', default=[])

    (options, args) = parser.parse_args()
    
    warnings = []
    args = ' '.join(args)
    if args:
        for arg in args:
            if os.path.isdir(arg):
                for dirpath, dirnames, filenames in os.walk(arg):
                    for filename in filenames:
                        if filename.endswith('.py'):
                            warnings += checkPath(os.path.join(dirpath, filename), options.exclude)
            else:
                warnings += checkPath(arg, options.exclude)
    else:
        warnings += check(sys.stdin.read(), '<stdin>')

    raise SystemExit(sum(1 for w in warnings if w.level == 'E') > 0)
