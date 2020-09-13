'''
Created on Sep 12, 2020

@author: ballance
'''

class TypeList(object):
    
    def __init__(self, t):
        self.t = t
        
    def accept(self, v):
        v.visitTypeList(self)