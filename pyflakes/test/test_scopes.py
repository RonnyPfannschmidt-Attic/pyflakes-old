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

    def test_unused_uncommon_gets_propagated(self):
        self.flakes("""
            if True:
                a = 1
                b = 2
            else:
                a = 2
            print (a, b)
        """)

    def test_uncommon_but_used_in_scope_still_warns(self):
        #XXX: message sucks
        self.flakes("""
        if True:
            a = 1
            b = 2
            b  # use it, so the unused propagation wont fire
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

    def test_return_in_else_will_propagate_body(self):
        self.flakes("""
            if True:
                a = 1
            else:
                return ValueError
            print(a)
        """, m.ExceptionReturn)

    def test_return_in_body_will_propagate_else(self):
        self.flakes("""
            if True:
                return ValueError
            else:
                a = 1
            print(a)
        """, m.ExceptionReturn)

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


    def test_nested_id_wont_mess(self):
        self.flakes("""
            if 1:
                var = 1
                if var:
                    woo = var.fun
            """)

    def test_del_in_if(self):
        #XXX:
        self.flakes("""
            var = 1
            if var:
                del var
        """)

    def test_execnet_channelexec_name_defines_channel(self):
        self.flakes("""
        if __name__ == '__channelexec__':
            channel.send('works')
        """)

    def test_execnet_channelexec_defines_channel_only_after_check(self):
        self.flakes("""
            channel
            if __name__ == '__channelexec__':
                channel.send('works')
        """, m.UndefinedName)

    def test_tracebackhide_needs_no_using_is_ok(self):
        self.flakes("""
            def helper():
                __tracebackhide__ = True
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

    def test_body_availiable_in_else(self):
        self.flakes("""
            try:
                from lxml import etree
            except ImportError:
                print('missing')
            else:
                print(etree)
            """)

    def test_lotsa_local_scopes(self):
        """code from mercurial that gave the condition code hickups"""
        self.flakes("""
        import os
        short = _ = lambda x:x
        import util
        def makefilename(repo, pat, node,
                         total=None, seqno=None,
                         revwidth=None, pathname=None):
            node_expander = {
                'H': lambda: hex(node),
                'R': lambda: str(repo.changelog.rev(node)),
                'h': lambda: short(node),
                }
            expander = {
                '%': lambda: '%',
                'b': lambda: os.path.basename(repo.root),
                }

            try:
                if node:
                    expander.update(node_expander)
                if node:
                    expander['r'] = (lambda:
                            str(repo.changelog.rev(node)).zfill(revwidth or 0))
                if total is not None:
                    expander['N'] = lambda: str(total)
                if seqno is not None:
                    expander['n'] = lambda: str(seqno)
                if total is not None and seqno is not None:
                    expander['n'] = lambda: str(seqno).zfill(len(str(total)))
                if pathname is not None:
                    expander['s'] = lambda: os.path.basename(pathname)
                    expander['d'] = lambda: os.path.dirname(pathname) or '.'
                    expander['p'] = lambda: pathname

                newname = []
                patlen = len(pat)
                i = 0
                while i < patlen:
                    c = pat[i]
                    if c == '%':
                        i += 1
                        c = pat[i]
                        c = expander[c]()
                    newname.append(c)
                    i += 1
                return ''.join(newname)
            except KeyError, inst:
                raise util.Abort(_("invalid format spec '%%%s' in output filename") %
                                 inst.args[0])
        """)
