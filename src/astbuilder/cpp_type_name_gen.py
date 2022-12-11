
from astbuilder.ast_enum import AstEnum
from astbuilder.ast_flags import AstFlags
from .ast_struct import AstStruct
from astbuilder.type_pointer import PointerKind
from astbuilder.type_scalar import TypeScalar, TypeKind

from .type_pointer import TypePointer
from .visitor import Visitor


class CppTypeNameGen(Visitor):
    
    def __init__(self, 
                 compressed=False, 
                 is_ret=False,
                 is_ref=False,
                 is_ptr=False,
                 is_const=False):
        self.out = ""
        self.compressed = compressed
        self.is_ret = is_ret
        self.is_ref = is_ref
        self.is_ptr = is_ptr
        self.is_const = is_const
        self.depth = 0
        
    def gen(self, t):
        t.accept(self)
        return self.out
    
    def visitTypeList(self, t):
        if self.depth == 0:
            self.depth += 1
            if self.is_const:
                self.out += "const "
            
            self.out += "std::vector<"
            self.out += CppTypeNameGen(compressed=self.compressed).gen(t.t)
            self.out += ">"
        
            if self.is_ret:
                self.out += " &"
            self.depth -= 1
        else:
            self.out += CppTypeNameGen().gen(t)

    def visitTypeMap(self, t):
        if self.depth == 0:
            self.depth += 1
            if self.is_const:
                self.out += "const "
            
            self.out += "std::map<"
            self.out += CppTypeNameGen(compressed=self.compressed).gen(t.kt)
            self.out += ","
            self.out += CppTypeNameGen(compressed=self.compressed).gen(t.vt)
            self.out += ">"
        
            if self.is_ret:
                self.out += " &"
            self.depth -= 1
        else:
            self.out += CppTypeNameGen().gen(t)            
        
    def visitTypePointer(self, t : TypePointer):
        if self.depth == 0:
            self.depth += 1
            if not self.compressed:
                if t.pt == PointerKind.Shared:
                    self.out += "std::shared_ptr<"
                elif t.pt == PointerKind.Unique and not self.is_ret:
                    self.out += "std::unique_ptr<"
            Visitor.visitTypePointer(self, t)
            
        
            if t.pt == PointerKind.Shared or t.pt == PointerKind.Unique:
                if not self.compressed:
                    if self.is_ret:
                        if t.pt == PointerKind.Shared:
                            self.out += ">"
                        else:
                            self.out += "*"
                    else:
                        self.out += ">"
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
            self.out += CppTypeNameGen().gen(t)

    def visitTypeScalar(self, t : TypeScalar):
        vmap = {
            TypeKind.String : "std::string",
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
        # TODO: do we know if this is a class or an enum?
        if not isinstance(t.target, (AstEnum,AstFlags,AstStruct)):
            self.out += "I" + t.name
        else:
            self.out += t.name
        if self.is_ptr:
            self.out += " *"
        if self.is_ref:
            self.out += " &"
        
        
