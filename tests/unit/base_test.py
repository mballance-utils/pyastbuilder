'''
Created on Mar 21, 2021

@author: mballance
'''
import io
from unittest.case import TestCase

from astbuilder.ast import Ast
from astbuilder.parser import Parser
from astbuilder.linker import Linker
import os
import shutil


class BaseTest(TestCase):
    
    def setUp(self):
        self.testdir = os.path.join(
            os.getcwd(),
            "rundir",
            self.id())
        print("testdir: " + self.testdir)
        if os.path.isdir(self.testdir):
            shutil.rmtree(self.testdir)
        os.makedirs(self.testdir)
        
    def tearDown(self):
        TestCase.tearDown(self)
        pass
    
    def loadAst(self, doc):
        ast = Ast()

        f = io.StringIO(doc)        
        Parser(ast).parse(f)
        
        Linker().link(ast)
        
        return ast
        