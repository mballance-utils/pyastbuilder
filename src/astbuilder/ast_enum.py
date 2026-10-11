'''
Created on Sep 13, 2020

@author: ballance
'''

class AstEnum(object):
    
    def __init__(self, name):
        self.name = name
        self.values = []
        # Documentation-only: value name -> `doc:` text, and value name ->
        # 1-based YAML line. `values` keeps its existing shape for the
        # generators.
        self.value_docs = {}
        self.value_lines = {}
        self.value_doclines = {}
        self.doc = None
        self.srcfile = None
        self.srcline = -1
        self.docline = -1
    
    def accept(self, v):
        v.visitAstEnum(self)
        
        