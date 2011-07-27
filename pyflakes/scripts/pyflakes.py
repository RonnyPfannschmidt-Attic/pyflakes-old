
"""
Implementation of the command-line I{pyflakes} tool.
"""

import sys
import os
import _ast

checker = __import__('pyflakes.checker').checker

def check(codeString, filename, stderr=sys.stderr):
    """
    Check the Python source given by C{codeString} for flakes.

    @param codeString: The Python source to check.
    @type codeString: C{str}

    @param filename: The name of the file the source came from, used to report
        errors.
    @type filename: C{str}

    @return: The number of warnings emitted.
    @rtype: C{int}
    """
    # First, compile into an AST and handle syntax errors.
    try:
        try:
            tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)
            lnooffset = 0
        # the weird position of value is necessary cause
        # the hack masks original exception texts
        except SyntaxError, value:
            # HACK: try again with print function
            tree = compile('from __future__ import print_function\n' +
                           codeString, filename, "exec", _ast.PyCF_ONLY_AST)
            lnooffset = 1
    except SyntaxError:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if (text is None and
            'keyword' not in msg and
            'non-default' not in msg):

            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            print >> stderr, "%s: problem decoding source" % (filename, )
        else:
            line = codeString.splitlines()[lineno-1].rstrip()

            if offset is not None:
                offset = offset - (len(text) - len(line))

            print >> stderr, '%s:%d: %s' % (filename, lineno, msg)
            print >> stderr, line

            if offset is not None:
                print >> stderr, " " * offset, "^"

        return 1
    else:
        # Okay, it's syntactically valid.  Now check it.
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        for warning in w.messages:
            warning.lineno -= lnooffset
            print warning
        return len(w.messages)


def checkPath(filename, stderr=None):
    """
    Check the given path, printing out any warnings detected.

    @return: the number of warnings printed
    """
    try:
        content = open(filename, 'U').read() + '\n'
    except IOError, msg:
        print >> stderr, "%s: %s" % (filename, msg.args[1])
        return 1
    return check(content, filename, stderr=stderr)


def main():
    warnings = 0
    args = sys.argv[1:]
    if args:
        for arg in args:
            if os.path.isdir(arg):
                for dirpath, dirnames, filenames in os.walk(arg):
                    for filename in sorted(filenames):
                        if filename.endswith('.py'):
                            warnings += checkPath(os.path.join(dirpath, filename))
            else:
                warnings += checkPath(arg)
    else:
        warnings += check(sys.stdin.read(), '<stdin>')

    raise SystemExit(warnings > 0)
