'''
Created on May 28, 2022

@author: mballance
'''
from astbuilder.visitor import Visitor
from astbuilder.ast_class import AstClass

class PyExtGenPtrDef(Visitor):
    
    def __init__(self, decl_pxd):
        self.decl_pxd = decl_pxd
        
    def gen(self, ast):
        ast.accept(self)
        
    def visitAstClass(self, c : AstClass):
        self.decl_pxd.println("ctypedef I%s *I%sP" % (c.name, c.name))
