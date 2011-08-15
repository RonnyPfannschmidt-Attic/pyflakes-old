
import textwrap
import _ast

import unittest

from pyflakes import checker

def flakes(input, *expectedOutputs, **kw):
    ast = compile(textwrap.dedent(input), "<test>", "exec",
                  _ast.PyCF_ONLY_AST)
    w = checker.Checker(ast, **kw)
    outputs = [type(o) for o in w.messages]
    expectedOutputs = list(expectedOutputs)
    #XXX: use file order or message creation order instead
    assert sorted(outputs) == sorted(expectedOutputs)
    return w

class Test(unittest.TestCase):

    def flakes(self, input, *expectedOutputs, **kw):
        return flakes(input, *expectedOutputs, **kw)

