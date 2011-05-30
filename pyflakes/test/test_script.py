
"""
Tests for L{pyflakes.scripts.pyflakes}.
"""

import sys
from StringIO import StringIO

from unittest import TestCase
from pyflakes.scripts.pyflakes import check, checkPath
from pyflakes.scripts import pyflakes


class CheckTests(TestCase):
    """
    Tests for L{check} and L{checkPath} which check a file for flakes.
    """

    
    def test_missingTrailingNewline(self):
        """
        Source which doesn't end with a newline shouldn't cause any
        exception to be raised nor an error indicator to be returned by
        L{check}.
        """
        if sys.version < '2.7':
            return #XXX syntax error on older python
        content = "def foo():\n\tpass\n\t"
        self.assertFalse(check(content, 'dummy.py'))

    def test_checkPathNonExisting(self):
        """
        L{checkPath} handles non-existing files.
        """
        err = StringIO()
        try:
            def mock_open(*k):
                raise IOError(None, 'No such file or directory')
            pyflakes.open = mock_open
            count = checkPath('extremo', stderr=err)
        finally:
            del pyflakes.open
        self.assertEquals(err.getvalue(), 'extremo: No such file or directory\n')
        self.assertEquals(count, 1)


    def test_multilineSyntaxError(self):
        """
        Source which includes a syntax error which results in the raised
        L{SyntaxError.text} containing multiple lines of source are reported
        with only the last line of that source.
        """
        source = """\
def foo():
    '''

def bar():
    pass

def baz():
    '''quux'''
"""

        # Sanity check - SyntaxError.text should be multiple lines, if it
        # isn't, something this test was unprepared for has happened.
        try:
            compile(source, 'dummy.py', 'exec')
        except SyntaxError, exc:
            self.assertTrue(exc.text.count('\n') > 1)
        else:
            self.fail('uhm where is our syntax error')

        err = StringIO()
        count = check(source, 'dummy.py', stderr=err)
        self.assertEqual(count, 1)

        self.assertEqual(
            err.getvalue(),
            """\
dummy.py:8: invalid syntax
    '''quux'''
           ^
""")


    def test_eofSyntaxError(self):
        """
        The error reported for source files which end prematurely causing a
        syntax error reflects the cause for the syntax error.
        """
        source = "def foo("
        err = StringIO()
        count = check(source, 'dummy.py', stderr=err)
        self.assertEqual(count, 1)
        self.assertEqual(
            err.getvalue(),
            """\
dummy.py:1: unexpected EOF while parsing
def foo(
         ^
""")


    def test_nonDefaultFollowsDefaultSyntaxError(self):
        """
        Source which has a non-default argument following a default argument
        should include the line number of the syntax error.  However these
        exceptions do not include an offset.
        """
        source = """\
def foo(bar=baz, bax):
    pass
"""
        err = StringIO()
        count = check(source, 'dummy.py', stderr=err)
        self.assertEqual(count, 1)
        self.assertEqual(
            err.getvalue(),
            """\
dummy.py:1: non-default argument follows default argument
def foo(bar=baz, bax):
""")


    def test_nonKeywordAfterKeywordSyntaxError(self):
        """
        Source which has a non-keyword argument after a keyword argument should
        include the line number of the syntax error.  However these exceptions
        do not include an offset.
        """
        source = """\
foo(bar=baz, bax)
"""
        err = StringIO()
        count = check(source, 'dummy.py', stderr=err)
        self.assertEqual(count, 1)
        self.assertEqual(
            err.getvalue(),
            """\
dummy.py:1: non-keyword arg after keyword arg
foo(bar=baz, bax)
""")


    def test_permissionDenied(self):
        """
        If the a source file is not readable, this is reported on standard
        error.
        """
        err = StringIO()
        try:
            def mock_open(*k):
                raise IOError(None, 'Permission denied')
            pyflakes.open = mock_open
            count = checkPath('dummy.py', stderr=err)
        finally:
            del pyflakes.open

        self.assertEquals(count, 1)
        self.assertEquals(
            err.getvalue(), "dummy.py: Permission denied\n")


    def test_misencodedFile(self):
        """
        If a source file contains bytes which cannot be decoded, this is
        reported on stderr.
        """
        source = u"""\
# coding: ascii
x = "\N{SNOWMAN}"
""".encode('utf-8')
        err = StringIO()
        count = check(source, 'dummy.py', stderr=err)
        self.assertEquals(count, 1)
        self.assertEquals(
            err.getvalue(), "dummy.py: problem decoding source\n")
