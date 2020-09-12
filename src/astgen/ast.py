'''
Created on Sep 12, 2020

@author: ballance
'''

class Ast(object):
    
    def __init__(self):
        self.classes = []
        
    def accept(self, v):
        v.visitAst(self)
        
    