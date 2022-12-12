'''
Created on Sep 12, 2020

@author: ballance
'''

class AstData(object):
    
    def __init__(self, name, t, is_ctor):
        self.name = name
        self.t = t
        self.is_ctor = is_ctor
        self.init = None
        self.visit = True
        
    def accept(self, v):
        v.visitAstData(self)
        