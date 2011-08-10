
"""
Implementation of the command-line I{pyflakes} tool.
"""

import _ast
import sys
import os
import optparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

checker = __import__('pyflakes.checker').checker
CouldNotCompile = __import__('pyflakes.messages', {}, {}, ['CouldNotCompile']).CouldNotCompile

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
        tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)
    except (SyntaxError, IndentationError), value:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if text is None:
            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            messages = [CouldNotCompile(filename, value)]
        else:
            line = text.splitlines()[-1]

            if offset is not None:
                offset = offset - (len(text) - len(line))

            messages = [CouldNotCompile(filename, value, msg, line)]
    else:
        # Okay, it's syntactically valid.  Now check it.
        w = checker.Checker(tree, filename)
        messages = w.messages

    messages.sort(lambda a, b: cmp(a.lineno, b.lineno))

    return messages


def checkPath(filename):
    """
    Check the given path, printing out any warnings detected.

    @return: the number of warnings printed
    """
    # TODO: this should return messages like check would above for files not found
    try:
        return check(file(filename, 'U').read() + '\n', filename)
    except IOError, msg:
        print >> sys.stderr, "%s: %s" % (filename, msg.args[1])
        raise SystemExit

def main():
    def traverse_path(warnings, dirpath, dirnames, filenames):
        if dirpath.startswith('./'):
            dirpath = dirpath[2:]
        
        # Exclusions
        for p in options.exclude_files:
            if dirpath.startswith(p):
                return

        for filename in filenames:
            path = os.path.join(dirpath, filename)
            # Exclusions
            for p in options.exclude_files:
                if path.startswith(p):
                    return
            if filename.endswith('.py'):
                warnings += checkPath(path)
    
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
                for dirpath, dirnames, filenames in os.walk(arg):
                    traverse_path(messages, dirpath, dirnames, filenames)
            else:
                messages += checkPath(arg)
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


    failed = bool(sums.get('E'))

    if sums:
        print
        print '%s! %s' % (failed and 'Failed' or 'Done', ', '.join('%s=%s' % (k, v) for k, v in sorted(sums.iteritems())))

    raise SystemExit(failed)

if __name__ == '__main__':
    main()
