'''
Created on Sep 12, 2020

@author: ballance
'''
from astgen.ast_data import AstData
from astgen.ast import Ast

class Visitor(object):
    
    def __init__(self):
        pass
    
    def visitAst(self, ast : Ast):
        for cls in ast.classes:
            cls.accept(self)

    def visitAstClass(self, c):
        for d in c.data:
            d.accept(self)
            
    def visitAstData(self, d : AstData):
        d.t.accept(self)
        
    def visitTypeList(self, t):
        t.t.accept(self)
        
    def visitTypePointer(self, t):
        t.t.accept(self)
    
    def visitTypeScalar(self, t):
        pass
    
    def visitTypeUserDef(self, t):
        pass
    
    