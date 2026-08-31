"""List-accessor generation, per element shape.

`PyExtListAccessorGen.gen()` emits the ListUtil property unconditionally --

    def path(self) -> ListUtil:
        return ListUtil(self.numPath, self.getPath)

-- and *then* dispatches on the element type to generate `numPath`/`getPath`.
So an element shape with no visitor produces a property whose helpers do not
exist: an AttributeError at first use, and invisible until then.

That is exactly what happened to `list<value-struct>`, the one shape with no
`visitTypeUserDef`. These tests assert the invariant directly -- every emitted
property's helpers are emitted too -- so the next shape added to any schema
cannot reintroduce it quietly.
"""

import io
import os
import re
import shutil
from unittest.case import TestCase

from astbuilder.ast import Ast
from astbuilder.linker import Linker
from astbuilder.parser import Parser
from astbuilder.pyext_gen import PyExtGen


class TestListAccessors(TestCase):

    def setUp(self):
        self.testdir = os.path.join(os.getcwd(), "rundir", self.id())
        if os.path.isdir(self.testdir):
            shutil.rmtree(self.testdir)
        os.makedirs(self.testdir)

    def _gen(self, doc):
        """Generate the pyext for *doc* and return the .pyx text."""
        ast = Ast()
        Parser(ast).parse(io.StringIO(doc))
        Linker().link(ast)

        extdir = os.path.join(self.testdir, "ext")
        os.makedirs(extdir)
        PyExtGen(extdir, "ast", "test.ast", None, None).generate(ast)

        with open(os.path.join(extdir, "ast.pyx")) as fp:
            return fp.read()

    def _assert_helpers_exist(self, pyx):
        """Every ListUtil property has the two helpers it calls.

        This is the general guard. It reads the property bodies rather than
        naming fields, so it holds for any schema.
        """
        missing = []
        for num, get in re.findall(
                r"return ListUtil\(self\.(\w+), self\.(\w+)\)", pyx):
            for helper in (num, get):
                if not re.search(r"cpdef [\w\[\]\.']* ?%s\(self" % helper, pyx):
                    missing.append(helper)
        self.assertEqual(
            missing, [],
            "ListUtil properties call helpers that were never generated: %s"
            % missing)
        return len(re.findall(r"return ListUtil\(", pyx))

    def test_list_of_value_struct(self):
        """The shape that had no visitor at all."""
        doc = """
        structs:
        - Elem:
            - data:
                - kind: int32_t
                - idx: int32_t

        classes:
        - RefPath:
            - data:
                - path: list<Elem>
        """
        pyx = self._gen(doc)

        self.assertGreater(self._assert_helpers_exist(pyx), 0)

        # By value: the element is copied into its wrapper. There is no
        # ObjFactory/accept round-trip, which exists to recover the dynamic
        # type of a polymorphic pointer -- a value has none.
        self.assertIn("Elem.wrap(", pyx)
        self.assertIn("cpdef numPath(self)", pyx)

    def test_list_of_enum(self):
        """An enum element is an int at the boundary, like a scalar."""
        doc = """
        enums:
        - Kind:
            - A
            - B

        classes:
        - Holder:
            - data:
                - kinds: list<Kind>
        """
        pyx = self._gen(doc)
        self.assertGreater(self._assert_helpers_exist(pyx), 0)

    def test_list_of_pointer_and_scalar_still_work(self):
        """The two shapes that always worked, so the fix did not narrow them."""
        doc = """
        classes:
        - Child:
            - data:
                - v: int32_t
        - Parent:
            - data:
                - children: list<UP<Child>>
                - names: list<string>
        """
        pyx = self._gen(doc)
        self.assertGreaterEqual(self._assert_helpers_exist(pyx), 2)

    def test_every_shape_at_once(self):
        """The whole-schema version of the guard.

        A property with no helpers is a defect regardless of which field it
        belongs to, so the check that matters is over everything generated.
        """
        doc = """
        structs:
        - Elem:
            - data:
                - idx: int32_t

        enums:
        - Kind:
            - A
            - B

        classes:
        - Child:
            - data:
                - v: int32_t
        - Everything:
            - data:
                - elems: list<Elem>
                - kinds: list<Kind>
                - children: list<UP<Child>>
                - names: list<string>
                - nested: list<list<int32_t>>
        """
        pyx = self._gen(doc)
        self.assertGreaterEqual(self._assert_helpers_exist(pyx), 4)

    def test_the_emitted_iterator_satisfies_the_iterator_protocol(self):
        """`ListIterator` must be its own iterable.

        It had `__next__` and no `__iter__`, which is not an iterator: the
        protocol requires both. Python 3.12 did not notice, because
        `list(obj.field())` reaches `__next__` through `ListUtil.__iter__`
        without ever calling `iter()` on the result. Python 3.13 does notice,
        and `[x for x in obj.field()]` raises

            TypeError: 'ListIterator' object is not iterable

        So the defect presented as a scattered subset of a downstream suite
        failing on one interpreter version -- pssparser lost exactly one test
        on cp313 while cp312 stayed green -- rather than as anything pointing
        at this generator.

        The emitted helpers are plain Python, so this executes them rather
        than pattern-matching the text: the assertion is that they behave as
        an iterable on the interpreter running the test.
        """
        doc = """
        classes:
        - Holder:
            - data:
                - names: list<string>
        """
        pyx = self._gen(doc)

        m = re.search(
            r"^class ListIterator\(object\):.*?(?=^class ListUtil\()",
            pyx, re.S | re.M)
        self.assertIsNotNone(m, "ListIterator was not emitted at all")

        m2 = re.search(r"^class ListUtil\(object\):.*?(?=^\S|\Z)",
                       pyx, re.S | re.M)
        self.assertIsNotNone(m2, "ListUtil was not emitted at all")

        ns = {}
        exec(m.group(0) + "\n" + m2.group(0), ns)

        util = ns["ListUtil"](lambda: 3, lambda i: i * 10)

        # The call that always worked, so the fix did not narrow it.
        self.assertEqual(list(util), [0, 10, 20])

        # The call that broke on 3.13.
        self.assertEqual([x for x in util], [0, 10, 20])

        # The property itself, stated directly.
        it = iter(util)
        self.assertIs(iter(it), it)
        self.assertEqual([x for x in it], [0, 10, 20])
