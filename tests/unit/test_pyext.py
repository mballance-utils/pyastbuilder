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
        
        GenCPP(astdir, "ast", None, None).generate(ast)
        
        extdir = os.path.join(self.testdir, "ext")
        os.makedirs(extdir)
        
        PyExtGen(extdir, "ast", None, None).generate(ast)
        
        with open(os.path.join(self.testdir, "setup.py"), "w") as f:
            f.write(setup_py)

        
        