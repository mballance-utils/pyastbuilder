
class AstStruct(object):
    
    def __init__(self, name):
        self.name = name
        self.index = -1
        self.data = []
        
        self.deps = {}
        self.doc = None
        self.srcfile = None
        self.srcline = -1
        self.docline = -1
        
    def accept(self, v):
        v.visitAstStruct(self)