'''
Created on Sep 13, 2020

@author: ballance
'''
from astbuilder.visitor import Visitor
from astbuilder.ast_ref import AstRef

class Linker(Visitor):
    
    def __init__(self):
        self.active_class = None
        self.ast = None
        self.phase = 0
    
    def link(self, ast):
        self.ast = ast
        
        self.phase = 0
        ast.accept(self)
        
        self.phase = 1
        ast.accept(self)
        
    def visitAstClass(self, c):
        self.active_class = c
        Visitor.visitAstClass(self, c)
        
    def visitTypeUserDef(self, t):
        if not t.name in self.active_class.deps.keys():
            # Determine what this points to
            if t.name in self.ast.class_m.keys():
                ref = AstRef(self.ast.class_m[t.name])
                self.active_class.deps[t.name] = ref
                t.target = self.ast.class_m[t.name]
            elif t.name in self.ast.enum_m.keys():
                ref = AstRef(self.ast.enum_m[t.name])
                self.active_class.deps[t.name] = ref
                t.target = self.ast.enum_m[t.name]
            else:
                # TODO: add external classes later
                raise Exception("user-defined type " + t.name + " is not declared")
    
        