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
    # The phase that fills every field of the class (`set_by:`), or None for
    # the model's default phase. Documentation only; code generators ignore it.
    set_by : str = None
    
    def accept(self, v):
        v.visitAstClass(self)
        
    