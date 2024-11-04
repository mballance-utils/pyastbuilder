
from astbuilder.type_pointer import PointerKind
from astbuilder.type_scalar import TypeScalar, TypeKind

from .type_pointer import TypePointer
from .visitor import Visitor
from astbuilder.ast_enum import AstEnum
from astbuilder.ast_flags import AstFlags
from astbuilder.ast_struct import AstStruct


class PyExtTypeNameGenPyi(Visitor):
    
    def __init__(self, ns, is_ret=False):
        self.out = ""
        self.ns = ns
        self.is_ret = is_ret
        self.depth = 0
        
    def gen(self, t):
        self.out = ""
        t.accept(self)
        return self.out

    def visitAstEnum(self, e : AstEnum):
#        print("is_pydecl=%s is_pytype=%s" % (self.is_pydecl, self.is_pytype))
        self.out += e.name
    
    def visitAstFlags(self, f : AstFlags):
        self.out += f.name
    
    def visitTypeList(self, t):
        if self.depth == 0:
            self.depth += 1
            
            self.out += "List["
            self.out += PyExtTypeNameGenPyi(ns=self.ns).gen(t.t)
            self.out += "]"
        
            self.depth -= 1
        else:
            self.out += PyExtTypeNameGenPyi(ns=self.ns).gen(t)

    def visitTypeMap(self, t):
        if self.depth == 0:
            self.depth += 1
            
            self.out += "Dict["
            self.out += PyExtTypeNameGenPyi(ns=self.ns).gen(t.kt)
            self.out += ","
            self.out += PyExtTypeNameGenPyi(ns=self.ns).gen(t.vt)
            self.out += "]"
        
            self.depth -= 1
        else:
            self.out += PyExtTypeNameGenPyi(ns=self.ns).gen(t)
        
    def visitTypePointer(self, t : TypePointer):
        if self.depth == 0:
            self.depth += 1
            Visitor.visitTypePointer(self, t)
            self.depth -= 1
        else:
            self.out += PyExtTypeNameGenPyi(ns=self.ns).gen(t)

    def visitTypeScalar(self, t : TypeScalar):
        vmap = {
            TypeKind.String : "str",
            TypeKind.Bool : "bool",
            TypeKind.Int8: "int",
            TypeKind.Uint8: "int",
            TypeKind.Int16: "int",
            TypeKind.Uint16: "int",
            TypeKind.Int32: "int",
            TypeKind.Uint32: "int",
            TypeKind.Int64: "int",
            TypeKind.Uint64: "int",
            }
        self.out += vmap[t.t]
    
    def visitAstStruct(self, s : AstStruct):
        self.out += s.name

    def visitTypeUserDef(self, t):
        if isinstance(t.target, (AstEnum,AstFlags)):
            t.target.accept(self)
        elif isinstance(t.target, (AstStruct,)):
            self.out += "%s" % t.name
        else:
            self.out += "%s" % t.name
