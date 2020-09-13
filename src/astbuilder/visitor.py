'''
Created on Sep 12, 2020

@author: ballance
'''
from astbuilder.ast_data import AstData
from astbuilder.ast import Ast
from astbuilder.ast_enum import AstEnum

class Visitor(object):
    
    def __init__(self):
        pass
    
    def visitAst(self, ast : Ast):
        for cls in ast.classes:
            cls.accept(self)
        for enum in ast.enums:
            enum.accept(self)

    def visitAstClass(self, c):
        for d in c.data:
            d.accept(self)
            
    def visitAstData(self, d : AstData):
        d.t.accept(self)
        
    def visitAstEnum(self, e : AstEnum):
        pass
        
    def visitTypeList(self, t):
        t.t.accept(self)
        
    def visitTypePointer(self, t):
        t.t.accept(self)
    
    def visitTypeScalar(self, t):
        pass
    
    def visitTypeUserDef(self, t):
        pass
    
    