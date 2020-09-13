'''
Created on Sep 13, 2020

@author: ballance
'''

class AstEnum(object):
    
    def __init__(self, name):
        self.name = name
        self.values = []
    
    def accept(self, v):
        v.visitAstEnum(self)
        
        