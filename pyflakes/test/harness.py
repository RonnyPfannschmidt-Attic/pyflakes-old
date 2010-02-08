
import textwrap

from twisted.trial import unittest

from pyflakes import checker


class Test(unittest.TestCase):

    def flakes(self, input, *expectedOutputs, **kw):
        # 0x400 is the compile flag PyCF_ONLY_AST
        ast = compile(textwrap.dedent(input), "<test>", "exec", 0x400)
        w = checker.Checker(ast, **kw)
        outputs = [type(o) for o in w.messages]
        expectedOutputs = list(expectedOutputs)
        outputs.sort()
        expectedOutputs.sort()
        self.assert_(outputs == expectedOutputs, '''\
for input:
%s
expected outputs:
%s
but got:
%s''' % (input, repr(expectedOutputs), '\n'.join([str(o) for o in w.messages])))
        return w
