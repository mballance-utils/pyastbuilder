
from astbuilder.type_pointer import PointerKind
from astbuilder.type_scalar import TypeScalar, TypeKind

from .type_pointer import TypePointer
from .visitor import Visitor
from astbuilder.ast_enum import AstEnum


class PyExtTypeNameGen(Visitor):
    
    def __init__(self, 
                 compressed=False, 
                 is_pytype=False,
                 is_pydecl=False,
                 is_ret=False,
                 is_ref=False,
                 is_ptr=False,
                 is_const=False):
        self.out = ""
#        self.compressed = compressed
        self.compressed = False
        self.is_pytype = is_pytype
        self.is_pydecl = is_pydecl
        self.is_ret = is_ret
        self.is_ref = is_ref
        self.is_ptr = is_ptr
        self.is_const = is_const
        self.depth = 0
        
    def gen(self, t):
        self.out = ""
        t.accept(self)
        return self.out
    
    def visitTypeList(self, t):
        if self.depth == 0:
            self.depth += 1
            if self.is_const:
                self.out += "const "
            
            self.out += "std_vector["
            self.out += PyExtTypeNameGen(
                compressed=self.compressed,
                is_pytype=self.is_pytype,
                is_pydecl=self.is_pydecl).gen(t.t)
            self.out += "]"
        
            if self.is_ret:
                self.out += " &"
            self.depth -= 1
        else:
            self.out += PyExtTypeNameGen().gen(t)

    def visitTypeMap(self, t):
        if self.depth == 0:
            self.depth += 1
            if self.is_const:
                self.out += "const "
            
            self.out += "std_map["
            self.out += PyExtTypeNameGen(
                compressed=self.compressed,
                is_pydecl=self.is_pydecl,
                is_pytype=self.is_pytype).gen(t.kt)
            self.out += ","
            self.out += PyExtTypeNameGen(
                compressed=self.compressed,
                is_pydecl=self.is_pydecl,
                is_pytype=self.is_pytype).gen(t.vt)
            self.out += "]"
        
            if self.is_ret:
                self.out += " &"
            self.depth -= 1
        else:
            self.out += PyExtTypeNameGen().gen(t)            
        
    def visitTypePointer(self, t : TypePointer):
        if self.depth == 0:
            self.depth += 1
            if self.is_pytype:
                # Just display the name
                Visitor.visitTypePointer(self, t)
            else:
                if not self.compressed:
                    if t.pt == PointerKind.Shared:
                        self.out += "shared_ptr["
                    elif t.pt == PointerKind.Unique and not self.is_ret:
                        self.out += "unique_ptr["
                Visitor.visitTypePointer(self, t)
            
        
                if t.pt == PointerKind.Shared or t.pt == PointerKind.Unique:
                    if not self.compressed:
                        if self.is_ret:
                            if t.pt == PointerKind.Shared:
                                self.out += "]"
                            else:
                                self.out += "*"
                        else:
                            self.out += "]"
                    else:
                        if self.is_ret:
                            if t.pt == PointerKind.Shared:
                                self.out += "SP"
                            else:
                                self.out += "*"
                        else:
                            self.out += "SP" if t.pt == PointerKind.Shared else "UP"
                else:
                    self.out += " *"
            self.depth -= 1
        else:
            self.out += PyExtTypeNameGen().gen(t)

    def visitTypeScalar(self, t : TypeScalar):
        vmap = {
            TypeKind.String : "std_string",
            TypeKind.Bool : "bool",
            TypeKind.Int8: "int8_t",
            TypeKind.Uint8: "uint8_t",
            TypeKind.Int16: "int16_t",
            TypeKind.Uint16: "uint16_t",
            TypeKind.Int32: "int32_t",
            TypeKind.Uint32: "uint32_t",
            TypeKind.Int64: "int64_t",
            TypeKind.Uint64: "uint64_t",
            }
        if self.is_const:
            self.out += "const "
        self.out += vmap[t.t]
        if self.is_ref:
            self.out += " &"
    
    def visitTypeUserDef(self, t):
        if self.is_const:
            self.out += "const "
        if not isinstance(t.target, AstEnum):
            if self.is_pydecl:
                self.out += "I%s" % t.name
            else:
                self.out += "%s" % t.name
        else:
            # Type names are omitted in Pyx
            if self.is_pydecl:
                self.out += t.name
        if self.is_ptr:
            if not self.is_pytype:
                self.out += "P "
            else:
                self.out += " "
        if self.is_ref:
            self.out += " &"
        
        