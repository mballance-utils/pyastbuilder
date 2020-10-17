'''
Created on Oct 16, 2020

@author: ballance
'''

class TypeMap(object):
    
    def __init__(self, kt, vt):
        self.kt = kt
        self.vt = vt

    def accept(self, v):
        v.visitTypeMap(self)
        