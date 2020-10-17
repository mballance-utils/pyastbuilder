'''
Created on Oct 15, 2020

@author: ballance
'''

class AstFlags(object):
    
    def __init__(self, name):
        self.name = name
        self.values = []
        
    def accept(self, v):
        v.visitAstFlags(self) 
        