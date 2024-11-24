
from astbuilder.type_pointer import PointerKind
from astbuilder.type_scalar import TypeScalar, TypeKind

from .type_pointer import TypePointer
from .visitor import Visitor
from astbuilder.ast_class import AstClass
from astbuilder.ast_enum import AstEnum
from astbuilder.ast_flags import AstFlags
from astbuilder.ast_struct import AstStruct

# pydecl - captures whether we are in a context where a C++ type must be namespace-qualified
# pytype - When true, we want to refer to the 'Python' version of a class type
#          When false, we want to refer to the wrapped C++ version of a class type
#
# pydecl, pytype
# True    True    - In a .pxd file referring to a Python type (empty for Enum)
# False   True    - In a .pyx file referring to a Python type (empty for Enum)
# True    False   - We're in a declaration scope (unclear .pxd or _decl.pxd) using the non-Python type
#                   - Do not qualify with a namespace
#                   - Reference as I<type>
#                   - Use I<type>P for pointer types
# False   False   - We're in the _decl.pxd using a non-Python type

class PyExtRvalGen(Visitor):
    
    def __init__(self, ns, fp) :
        self.out = ""
        self.fp = fp
        self.ns = ns
        self.param = None
        self.depth = 0
        self.wrap_t = None
        
    def gen(self, param, t):
        self.out = ""
        self.param = param
        t.accept(self)
        if self.wrap_t is not None:
            self.fp.println("_obj_f = ObjFactory()")
            self.fp.println("%s.accept(_obj_f._hndl)" % self.out)
            self.fp.println("return _obj_f._obj")
        else:
            self.fp.println("return %s" % self.out)
        return self.out

    def visitAstEnum(self, e : AstEnum):
        self.out += "enum<" + self.param + ">"
    
    def visitAstFlags(self, f : AstFlags):
        self.out += "flags<" + self.param + ">"
    
    def visitTypeList(self, t):
        self.out += "list<" + self.param + ">"

    def visitTypeMap(self, t):
        if self.depth == 0:
            self.depth -= 1
        else:
            self.out += PyExtTypeNameGen(ns=self.ns).gen(t)
        
    def visitTypePointer(self, t : TypePointer):
        if self.depth == 0:
            if t.pt == PointerKind.Unique or t.pt == PointerKind.Shared:
                t.t.accept(self)
                self.out += ".get()"
            else:
                t.t.accept(self)
        else:
            self.out += self.param

    def visitTypeScalar(self, t : TypeScalar):
        if t.t == TypeKind.String:
            self.out += "%s.decode()" % self.param
        else:
            self.out += self.param
    
    def visitAstStruct(self, s : AstStruct):
        self.out += self.param

    def visitAstClass(self, c : AstClass):
        self.out += self.param
        self.wrap_t = c.name

    def visitTypeUserDef(self, t):
        print("PyCallParamGen: TypeUserDef")
        t.target.accept(self)

        