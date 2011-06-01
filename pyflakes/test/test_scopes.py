from .harness import Test
from pyflakes import messages as m

class ConditionalScopesTest(Test):
    def test_in_scopes(self):
        self.flakes("""
        x = 1
        if x:
            a = 1
        else:
            a = 2
        print a
        """)

    def test_uncommon_still_warns(self):
        #XXX: message sucks
        self.flakes("""
        if True:
            a = 1
            b = 2
        else:
            a = 2
        print (a, b)
        """, m.UndefinedName)

    def test_raise_in_else_will_propagate_body(self):
        self.flakes("""
            if True:
                a = 1
            else:
                raise ValueError
            print(a)
        """)
    
    def test_raise_in_body_will_propagate_else(self):
        self.flakes("""
            if True:
                raise ValueError
            else:
                a = 1
            print(a)
        """)


    def test_nested_propagation(self):
        self.flakes("""
            if True:
                a = 1
            else:
                if True:
                    a = 2
                else:
                    a = 1
            print(a)
        """)

class TryExceptScopeTests(Test):
    def test_simple_impotrt_error(self):
        self.flakes("""
            __all__ = ['json']
            try:
                import json
            except ImportError:
                import simplejson as json
        """)


    def test_etree_import_cascade(self):
        self.flakes("""
        __all__ = ['etree']
        try:
          from lxml import etree
        except ImportError:
          try:
            import xml.etree.cElementTree as etree
          except ImportError:
            try:
              import xml.etree.ElementTree as etree
            except ImportError:
              try:
                import cElementTree as etree
              except ImportError:
                try:
                  import elementtree.ElementTree as etree
                except ImportError:
                  raise ImportError('no elementree implementation found')
        """)
