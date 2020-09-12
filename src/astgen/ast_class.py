'''
Created on Sep 12, 2020

@author: ballance
'''

class AstClass(object):
    
    def __init__(self):
        self.name = None
        self.super = None
        self.data = []
        
    def accept(self, v):
        v.visitAstClass(self)
        
    