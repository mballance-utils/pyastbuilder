'''
Created on Sep 12, 2020

@author: ballance
'''
from enum import Enum, auto


class TypeScalar(Enum):
    String = auto()
    Uint8 = auto()
    Int8 = auto()
    Uint16 = auto()
    Int16 = auto()
    Uint32 = auto()
    Int32 = auto()
    Uint64 = auto()
    Int64 = auto()
    
    def __init__(self, t):
        self.t = t
        
    def accept(self, v):
        pass
    
    
    