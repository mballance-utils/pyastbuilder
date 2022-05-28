'''
Created on May 28, 2022

@author: mballance
'''
from astbuilder.visitor import Visitor
from astbuilder.ast import Ast

class CppGenFwdDecl(Visitor):
    
    def __init__(self, out):
        self.out = out
        
    def gen(self, ast : Ast):
        ast.accept(self)
        
    def visitAstClass(self, c):
        self.out.println("class I%s;" % c.name)
        