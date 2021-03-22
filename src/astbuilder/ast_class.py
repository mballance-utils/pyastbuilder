'''
Created on Sep 12, 2020

@author: ballance
'''

class AstClass(object):
    
    def __init__(self, name):
        self.name = name
        self.super = None
        self.index = -1
        self.data = []
        
        self.deps = {}
        
    def accept(self, v):
        v.visitAstClass(self)
        
    