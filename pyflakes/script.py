
"""
Implementation of the command-line I{pyflakes} tool.
"""

import _ast
import sys
import os
import optparse

from pyflakes import checker
from pyflakes.messages import CouldNotCompile

def check(codeString, filename):
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
            return [CouldNotCompile(filename, value, "problem decoding source", 0)]
        else:
            line = codeString.splitlines()[lineno-1].rstrip()

            if offset is not None:
                offset = offset - (len(text) - len(line))
            #XXX: include offset?!
            return [CouldNotCompile(filename, value, msg, line)]
    else:
        # Okay, it's syntactically valid.  Now check it.
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        for warning in w.messages:
            warning.lineno -= lnooffset
        return w.messages


def checkPath(filename):
    """
    Check the given path, printing out any warnings detected.

    @return: the number of warnings printed
    """
    try:
        content = open(filename, 'U').read() + '\n'
    except IOError, msg:
        return [CouldNotCompile(filename, msg, msg.args[1], '')]
    return check(content, filename)


def walk_pyfiles_of(arg, exclude_files):
    for dirpath, dirnames, filenames in os.walk(arg):
        dirpath = os.path.normpath(dirpath)

        # Exclusions
        # XXX: this seems like a weird fuzzy hack
        def excluded(name):
            for p in exclude_files:
                if name.startswith(p):
                    return True

        if excluded(dirpath):
            continue

        for filename in sorted(filenames):
            path = os.path.join(dirpath, filename)
            if not excluded(path) and filename.endswith('.py'):
                yield path

def main():
    parser = optparse.OptionParser(usage='usage: %prog [options] module')
    parser.add_option('-x', '--exclude', action='append', dest='exclude', help='exclude levels', default=[])
    parser.add_option('-X', '--exclude-files', action='append', dest='exclude_files', help='exclude files', default=[])

    (options, args) = parser.parse_args()
    messages = []
    if args:
        for arg in args:
            if os.path.isdir(arg):
                if arg == '.':
                    arg = './'
                for pyfile in walk_pyfiles_of(arg, options.exclude_files):
                    messages.extend(checkPath(pyfile))
            else:
                messages.extend(checkPath(arg))
    else:
        messages += check(sys.stdin.read(), '<stdin>')


    sums = {}
    for message in messages:
        if message.level not in options.exclude:
            if message.level not in sums:
                sums[message.level] = 1
            else:
                sums[message.level] += 1
            print message


    failed = 'E' in sums

    if sums:
        print
        print '%s! %s' % (failed and 'Failed' or 'Done', ', '.join('%s=%s' % (k, v) for k, v in sorted(sums.iteritems())))

    raise SystemExit(failed)

if __name__ == '__main__':
    main()
