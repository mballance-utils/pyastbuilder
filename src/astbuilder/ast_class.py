'''
Created on Sep 12, 2020

@author: ballance
'''
import dataclasses as dc
from typing import List, Dict
from .ast_base import AstBase

@dc.dataclass
class AstClass(AstBase):
    super : object = None
    index : int = -1
    data : List = dc.field(default_factory=list)
    deps : Dict = dc.field(default_factory=dict)
    
    def accept(self, v):
        v.visitAstClass(self)
        
    