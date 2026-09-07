'''
Created on Sep 13, 2020

@author: ballance
'''
from astbuilder.visitor import Visitor
from astbuilder.ast_ref import AstRef
from toposort import toposort, toposort_flatten

#>>> list(toposort({2: {11},
#...                9: {11, 8, 10},
#...                10: {11, 3},
#...                11: {7, 5},
#...                8: {7, 3},
#...               }))
#[{3, 5, 7}, {8, 11}, {2, 10}, {9}]

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
        
        # Now, sort classes in dependency order
        for i,c in enumerate(self.ast.classes):
            c.index = i
            
        sort_d = {}
        for i,c in enumerate(self.ast.classes):
            d = set()
            if c.super is not None:
                d.add(c.super.target.index)
            sort_d[i] = d
            
        sort_order = list(toposort(sort_d))

        classes = []        
        for o in sort_order:
            for i in o:
                classes.append(ast.classes[i])
                
        ast.classes = classes

        
    def visitAstClass(self, c):
        self.active_class = c
        Visitor.visitAstClass(self, c)

    def visitAstStruct(self, s):
        self.active_class = s
        Visitor.visitAstStruct(self, s)
        
    def visitTypeUserDef(self, t):
        # Resolve the target on *every* reference.
        #
        # This used to sit inside the `deps` guard below, so only a class's
        # first reference to a given type was resolved: a second field of the
        # same user-defined type kept target=None, and the generators that
        # dereference it (pyext_accessor_gen.visitTypeUserDef) died with an
        # AttributeError far from the cause.  The guard belongs to `deps`,
        # which exists to emit each include once -- it was never about the
        # target.
        if t.name in self.ast.class_m.keys():
            target = self.ast.class_m[t.name]
        elif t.name in self.ast.struct_m.keys():
            target = self.ast.struct_m[t.name]
        elif t.name in self.ast.enum_m.keys():
            target = self.ast.enum_m[t.name]
        elif t.name in self.ast.flags_m.keys():
            target = self.ast.flags_m[t.name]
        else:
            # TODO: add external classes later
            raise Exception("user-defined type " + t.name + " is not declared")

        t.target = target

        if not t.name in self.active_class.deps.keys():
            self.active_class.deps[t.name] = AstRef(target)
    
        