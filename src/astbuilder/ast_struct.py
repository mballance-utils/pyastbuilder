
class AstStruct(object):
    
    def __init__(self, name):
        self.name = name
        self.index = -1
        self.data = []
        
        self.deps = {}
        
    def accept(self, v):
        v.visitAstStruct(self)