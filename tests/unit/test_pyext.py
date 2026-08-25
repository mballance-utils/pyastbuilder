'''
Created on Mar 21, 2021

@author: mballance
'''
from unit.base_test import BaseTest
from astbuilder.gen_cpp import GenCPP
from astbuilder.pyext_gen import PyExtGen
import importlib
import os
import subprocess
import sys
import shutil

# Builds the generated .pyx together with the generated C++ AST sources, so the
# factory implementation lives inside the extension itself.
SETUP_PY = """
import os
import sys

from setuptools import Extension, setup
from Cython.Build import cythonize

setup_dir=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(setup_dir, "ext"))

import ast_ext

ext = ast_ext.ext()

ast_dir=os.path.join(setup_dir, 'ast')
ext.include_dirs.append(ast_dir)
ext.include_dirs.append(os.path.join(ast_dir, 'include'))
ext.include_dirs.append(os.path.join(ast_dir, 'include', 'impl'))
for f in os.listdir(ast_dir):
    file = os.path.join(ast_dir, f)
    if os.path.isfile(file) and os.path.splitext(f)[1] == ".cpp":
        ext.sources.append(file)

setup(
    name="ast",
    version="0.0.1",
    ext_modules=cythonize([ext])
    )
"""


class TestPyExt(BaseTest):

    def _build_ast(self, doc, namespace=None):
        """Generate, compile and import the extension for `doc`.

        Returns the imported `ast` extension module. Each test gets its own
        package name so the four extensions built by this file don't collide
        in sys.modules.
        """
        ast = self.loadAst(doc)

        # The C++ and pyext generators must agree on the library name: the pyx
        # resolves the factory through the `<name>_getFactory` entry point that
        # GenCPP emits.
        name = "ast"
        pkg = self._testMethodName

        astdir = os.path.join(self.testdir, "ast")
        os.makedirs(astdir)
        GenCPP(astdir, name, None, namespace).generate(ast)

        extdir = os.path.join(self.testdir, "ext")
        os.makedirs(extdir)
        PyExtGen(extdir, name, "%s.%s" % (pkg, name), None, namespace).generate(ast)

        with open(os.path.join(self.testdir, "setup.py"), "w") as f:
            f.write(SETUP_PY)

        pkgdir = os.path.join(self.testdir, pkg)
        os.makedirs(pkgdir, exist_ok=True)
        with open(os.path.join(pkgdir, "__init__.py"), "w") as fp:
            fp.write("\n")
        for f in ("ast_decl.pxd", "ast.pxd"):
            shutil.copy(os.path.join(extdir, f), os.path.join(pkgdir, f))

        ret = subprocess.call(
            [sys.executable, "setup.py", "build_ext", "--inplace"],
            cwd=self.testdir)
        self.assertEqual(ret, 0)

        # Factory.inst() dlopen's the core library by name. Here the factory is
        # linked into the extension itself, so point that name at the extension.
        built = [f for f in os.listdir(pkgdir) if f.endswith((".so", ".pyd", ".dylib"))]
        self.assertEqual(len(built), 1, "expect exactly one built extension: %s" % built)
        if sys.platform == 'darwin':
            libname = "lib%s.dylib" % name
        elif sys.platform == 'win32':
            libname = "%s.dll" % name
        else:
            libname = "lib%s.so" % name
        os.symlink(built[0], os.path.join(pkgdir, libname))

        sys.path.insert(0, self.testdir)
        self.addCleanup(sys.path.remove, self.testdir)
        importlib.invalidate_caches()

        return importlib.import_module("%s.%s" % (pkg, name))

    def _check_c1_c2(self, testast, mkC1, mkC2):
        """Exercise the accessors, list accessors and visitor of a C1/C2 AST.

        `mkC1`/`mkC2` take the factory and build an instance, so the enum
        variant can supply its extra field.
        """
        factory = testast.Factory.inst()

        c2_i = mkC2(factory)
        self.assertEqual(c2_i.getF3(), "abc")

        # List accessors: add, count, index and iterate
        c2_i.addChild(mkC1(factory))
        c2_i.addChild(mkC1(factory))
        self.assertEqual(c2_i.numChildren(), 2)
        self.assertEqual(len(c2_i.getChildren()), 2)
        self.assertEqual(len(list(c2_i.children())), 2)
        self.assertIsInstance(c2_i.getChild(0), testast.C1)

        class MyVisitor(testast.VisitorBase):

            def __init__(self):
                super().__init__()
                self.n_c1 = 0
                self.n_c2 = 0

            def visitC1(self, i):
                self.n_c1 += 1

            def visitC2(self, i):
                self.n_c2 += 1
                super().visitC2(i)

        v = MyVisitor()
        for _ in range(1000):
            c2_i.accept(v)

        self.assertEqual(v.n_c2, 1000)
        # visitC2's base implementation chains to the C1 visitor for c2_i
        # itself and then descends into its two children
        self.assertEqual(v.n_c1, 3*1000)

    C1_C2_DOC = """
        classes:
        - C1:
            - data:
                - f1 : int32_t
                - f2 : bool
        - C2:
            - super: C1
            - data:
                - f3: string
                - f4: int32_t
                - children: list<UP<C1>>
        """

    def test_smoke(self):
        testast = self._build_ast(self.C1_C2_DOC)
        self._check_c1_c2(
            testast,
            lambda f: f.mkC1(1, False),
            lambda f: f.mkC2(1, False, "abc", 4))

    def test_smoke_ns1(self):
        testast = self._build_ast(self.C1_C2_DOC, "ns1")
        self._check_c1_c2(
            testast,
            lambda f: f.mkC1(1, False),
            lambda f: f.mkC2(1, False, "abc", 4))

    def test_smoke_ns2(self):
        testast = self._build_ast(self.C1_C2_DOC, "ns1::ns2")
        self._check_c1_c2(
            testast,
            lambda f: f.mkC1(1, False),
            lambda f: f.mkC2(1, False, "abc", 4))

    def test_smoke_enum_ns1(self):
        doc = """
        enums:
        - E1:
          - V1
          - V2
        classes:
        - C1:
            - data:
                - f1 : int32_t
                - f2 : bool
                - f3 : E1
        - C2:
            - super: C1
            - data:
                - f4: string
                - f5: int32_t
                - children: list<UP<C1>>
        """
        testast = self._build_ast(doc, "ns1")

        # C2 renames the string field, so check it under its own name and let
        # the shared check run against a C2 whose "abc" lives in f4.
        factory = testast.Factory.inst()
        c2_i = factory.mkC2(1, False, testast.E1.V1, "abc", 5)
        self.assertEqual(c2_i.getF4(), "abc")
        self.assertEqual(c2_i.getF3(), testast.E1.V1)

        c2_i.addChild(factory.mkC1(2, True, testast.E1.V2))
        self.assertEqual(c2_i.numChildren(), 1)
        self.assertEqual(c2_i.getChild(0).getF3(), testast.E1.V2)
