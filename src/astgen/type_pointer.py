'''
Created on Sep 12, 2020

@author: ballance
'''
from enum import Enum, auto

class PointerKind(Enum):
    Unique = auto()
    Shared = auto()
    Raw = auto()
    
class TypePointer(object):
    
    def __init__(self, pt, t=None):
        self.pt = pt
        self.t = t
        
    def accept(self, v):
        v.visitTypePointer(self)