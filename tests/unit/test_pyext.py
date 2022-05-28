'''
Created on Mar 21, 2021

@author: mballance
'''
from unittest.case import TestCase
from unit.base_test import BaseTest
import io
from astbuilder.pyext_gen_pxd import PyExtGenPxd
from astbuilder.outstream import OutStream
from astbuilder.gen_cpp import GenCPP
from astbuilder.pyext_gen import PyExtGen
import os
import subprocess
import sys
import shutil

class TestPyExt(BaseTest):
    
    def test_smoke(self):
        doc = """
        classes:
        - c1:
            - data:
                - f1 : int32_t
                - f2 : bool
        - c2:
            - super: c1
            - data:
                - f3: string
                - f4: int32_t
                - children: list<UP<c1>>
        """
        
        setup_py = """
import os
import sys

from setuptools import Extension, setup
from Cython.Build import cythonize

setup_dir=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(setup_dir, "ext"))

import ast_ext


VERSION="0.0.1"
PLATFORMS = "Any"

ext = ast_ext.ext()

for e in dir(ext):
    print("e: " + str(e))
   
ast_dir=os.path.join(setup_dir, 'ast')
ext.include_dirs.append(ast_dir)
ext.include_dirs.append(os.path.join(ast_dir, 'include'))
ext.include_dirs.append(os.path.join(ast_dir, 'include', 'impl'))
for f in os.listdir(ast_dir):
    file = os.path.join(ast_dir, f)
    if os.path.isfile(file) and os.path.splitext(f)[1] == ".cpp":
        print("Add: " + file)
        ext.sources.append(file)

extensions = [ext]

setup(
    name="libvsc",
    version="0.0.1",
    ext_modules=cythonize(extensions)
    )
        """
        
        print("Test: " + self._testMethodName + " " + self.id())
        
        ast = self.loadAst(doc)
        
        astdir = os.path.join(self.testdir, "ast")
        os.makedirs(astdir)
       
        name = "testast"
        GenCPP(astdir, name, None, None).generate(ast)
        
        extdir = os.path.join(self.testdir, "ext")
        os.makedirs(extdir)
        
        PyExtGen(extdir, "ast", "test.ast", None, None).generate(ast)
        
        with open(os.path.join(self.testdir, "setup.py"), "w") as f:
            f.write(setup_py)
            
        if not os.path.isdir(os.path.join(self.testdir, "test")):
            os.makedirs(os.path.join(self.testdir, "test"))
            with open(os.path.join(self.testdir, "test", "__init__.py"), "w") as fp:
                fp.write("\n")
        shutil.copy(
            os.path.join(self.testdir, "ext", "ast_decl.pxd"),
            os.path.join(self.testdir, "test", "ast_decl.pxd"))
        shutil.copy(
            os.path.join(self.testdir, "ext", "ast.pxd"),
            os.path.join(self.testdir, "test", "ast.pxd"))

        ret = subprocess.call(
            [sys.executable, "setup.py", "build_ext", "--inplace"],
            cwd=self.testdir
            )
        self.assertEqual(ret, 0)

        # Load just-compiled extension        
        sys.path.insert(0, self.testdir)
        import test
        from test import ast as testast
        
        for e in dir(testast):
            print("e: " + str(e))
        
        c2_i = testast.c2.create(1, False, "abc".encode(), 4)
        for e in dir(c2_i):
            print("e: " + str(e))
        print("f3=" + c2_i.get_f3().decode())
        self.assertEqual(c2_i.get_f3().decode(), "abc")
        
        class MyVisitor(testast.BaseVisitor):
            
            def __init__(self):
                super().__init__()
                
            def visitc1(self, i):
                print("visitc1")
                
            def visitc2(self, i):
                print("--> visitc2")
                super().visitc2(i)
                print("<-- visitc2")
                
        v = MyVisitor()
        for i in range(1000):
            c2_i.accept(v)
                
        
        