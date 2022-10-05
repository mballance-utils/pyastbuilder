'''
Created on Sep 12, 2020

@author: ballance
'''

class Ast(object):
    
    def __init__(self):
        self.classes = []
        self.class_m = {}
        self.structs = []
        self.struct_m = {}
        self.enums = []
        self.enum_m = {}
        self.flags = []
        self.flags_m = {}
        
    def addClass(self, c):
        if c.name in self.class_m.keys():
            raise Exception("Class " + c.name + " already declared")
        self.class_m[c.name] = c
        self.classes.append(c)

    def addStruct(self, s):
        if s.name in self.struct_m.keys():
            raise Exception("Struct " + s.name + " already declared")
        if s.name in self.class_m.keys():
            raise Exception("Struct " + s.name + " already declared as a class")
        self.struct_m[s.name] = s
        self.structs.append(s)
        
    def addEnum(self, e):
        if e.name in self.enum_m.keys():
            raise Exception("Enum " + e.name + " already declared")
        self.enum_m[e.name] = e
        self.enums.append(e)
        
    def addFlags(self, f):
        if f.name in self.flags_m.keys():
            raise Exception("Flags " + f.name + " already declared")
        self.flags_m[f.name] = f
        self.flags.append(f)
        
    def accept(self, v):
        v.visitAst(self)
        
    