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
        pass
    
    def link(self, ast):
        self.ast = ast
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
            elif t.name in self.ast.enum_m.keys():
                ref = AstRef(self.ast.enum_m[t.name])
                self.active_class.deps[t.name] = ref
            else:
                # TODO: add external classes later
                raise Exception("user-defined type " + t.name + " is not declared")
    
        