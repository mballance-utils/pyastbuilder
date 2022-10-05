'''
Created on Sep 12, 2020

@author: ballance
'''
from astbuilder.ast_data import AstData
from astbuilder.ast import Ast
from astbuilder.ast_enum import AstEnum
from astbuilder.ast_flags import AstFlags

class Visitor(object):
    
    def __init__(self):
        pass
    
    def visitAst(self, ast : Ast):
        for cls in ast.classes:
            cls.accept(self)
        for s in ast.structs:
            s.accept(self)
        for enum in ast.enums:
            enum.accept(self)
        for f in ast.flags:
            f.accept(self)

    def visitAstClass(self, c):
        if c.super is not None:
            c.super.accept(self)
        for d in c.data:
            d.accept(self)

    def visitAstStruct(self, s):
        for d in s.data:
            d.accept(self)
            
    def visitAstData(self, d : AstData):
        d.t.accept(self)
        
    def visitAstEnum(self, e : AstEnum):
        pass
    
    def visitAstFlags(self, f : AstFlags):
        pass
        
    def visitTypeList(self, t):
        t.t.accept(self)
        
    def visitTypeMap(self, t):
        t.kt.accept(self)
        t.vt.accept(self)
        
    def visitTypePointer(self, t):
        t.t.accept(self)
    
    def visitTypeScalar(self, t):
        pass
    
    def visitTypeUserDef(self, t):
        pass
    
    