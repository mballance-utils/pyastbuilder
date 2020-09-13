'''
Created on Sep 12, 2020

@author: ballance
'''
from enum import Enum, auto

class TypeKind(Enum):
    String = auto()
    Bool = auto()
    Uint8 = auto()
    Int8 = auto()
    Uint16 = auto()
    Int16 = auto()
    Uint32 = auto()
    Int32 = auto()
    Uint64 = auto()
    Int64 = auto()

class TypeScalar(object):
    
    def __init__(self, t : TypeKind):
        self.t = t
        
    def accept(self, v):
        v.visitTypeScalar(self)
    
    
    