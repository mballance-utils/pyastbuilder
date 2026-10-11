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
        # Documentation-only attributes; the code generators ignore them.
        self.doc = None
        # `rel:` on a raw-pointer field: "parent" (a back-pointer up the
        # containment tree) or "ref" (anything else). None means unstated,
        # which readers treat as "ref".
        self.rel = None
        # `set_by:` -- the phase that fills the field, or None for the
        # class's phase (AstClass.set_by) or the model's default.
        self.set_by = None
        self.srcfile = None
        self.srcline = -1
        self.docline = -1
        
    def accept(self, v):
        v.visitAstData(self)
        