'''
Created on Sep 12, 2020

@author: ballance
'''

class Ast(object):
    
    def __init__(self):
        self.classes = []
        self.class_m = {}
        self.enums = []
        self.enum_m = {}
        
    def addClass(self, c):
        if c.name in self.class_m.keys():
            raise Exception("Class " + c.name + " already declared")
        self.class_m[c.name] = c
        self.classes.append(c)
        
    def addEnum(self, e):
        if e.name in self.enum_m.keys():
            raise Exception("Enum " + e.name + " already declared")
        self.enum_m[e.name] = e
        self.enums.append(e)
        
    def accept(self, v):
        v.visitAst(self)
        
    