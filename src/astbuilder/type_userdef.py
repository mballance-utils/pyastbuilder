'''
Created on Sep 12, 2020

@author: ballance
'''

class TypeUserDef(object):
    
    def __init__(self, name):
        self.name = name
        
    def accept(self, v):
        v.visitTypeUserDef(self)
        