from astbuilder.pyext_type_name_gen import PyExtTypeNameGen
from astbuilder.type_pointer import PointerKind
from astbuilder.type_scalar import TypeKind
from astbuilder.visitor import Visitor
from .ast_enum import AstEnum
from .ast_flags import AstFlags


class PyExtAccessorGen(Visitor):
    # Integer and pointer
    # - const read accessor
    # - non-const write-value accessor
    #
    # String
    # - const-ref read accessor
    # - non-const write accessor
    #
    # List, Map
    # - const-ref read accessor
    # - non-const write accessor
    #
    #
    
    def __init__(self, name, clsname, decl_pxd, pxd, pyx):
        super().__init__()
        self.name = name
        self.clsname = clsname
        self.pxd = pxd
        self.decl_pxd = decl_pxd
        self.pyx = pyx
        self.field = None
        self.decl_pxd_ptr_tgen = PyExtTypeNameGen(
                ns=self.name,
                compressed=True,
                is_pydecl=False,
                is_pytype=False,
                is_ref=False,
                is_const=False)
        
    def gen(self, field):
        self.field = field
        self.field.t.accept(self)

    def visitTypeList(self, t):
        self.gen_collection_accessors(t)
    
    def visitTypeMap(self, t):
        self.gen_collection_accessors(t)
        
    def visitTypePointer(self, t):
        if t.pt == PointerKind.Raw:
            self.gen_rawptr_accessors(t)
        elif t.pt == PointerKind.Unique:
            self.gen_uptr_accessors(t)
        elif t.pt == PointerKind.Shared:
            self.gen_sptr_accessors(t)
        else:
            raise Exception("Accessor generation not supported for " + str(self.pt))

    def visitAstClass(self, c):
        self.gen_class_accessors(c)

    def visitAstStruct(self, s):
        print("TODO: gen struct accessor")

    def visitAstEnum(self, e : AstEnum):
        self.gen_enum_accessors(e)
    
    def visitAstFlags(self, f : AstFlags):
        self.gen_enum_accessors(f)

    def visitTypeScalar(self, t):
        if t.t == TypeKind.String:
            self.gen_string_accessors(t)
        else:
            self.gen_scalar_accessors(t)

    def visitTypeUserDef(self, t):
        print("--> visitTypeUserDef")
        t.target.accept(self)
        print("<-- visitTypeUserDef")
        pass
    
    def gen_collection_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        # Generate a read-only accessor
#        self.decl_pxd.println(self.const_ref_ret(t) + "get_" + self.field.name + "()")
#        self.decl_pxd.println()

        # Generate a non-const accessor
        self.decl_pxd.println(self.nonconst_ref_ret(
            t, 
            is_pydecl=False,
            is_pytype=False) + "get" + name + "();")
        
#         self.pyx.println("cdef %s get_%s():" % (self.nonconst_ref_ret(t), self.field.name))
#         self.pyx.inc_indent()
#         self.pyx.println("return (<%s_decl.%s *>self._hndl).get_%s()" %
#                          (self.name, self.clsname, self.field.name))
#         self.pyx.dec_indent()

    def gen_class_accessors(self, c):
        print("TODO: class accessor")
        pass


    def gen_enum_accessors(self, t):
        print("--> gen_enum_accessors %s" % self.field.name)
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        print("--> Generate decl_pxd")
        self.decl_pxd.println(
            self.decl_pxd_ptr_tgen.gen(t) + " get" + name + "()")
        self.decl_pxd.println()
        print("<-- Generate decl_pxd")
        
        
        self.pxd.println("cpdef %s get%s(self)" % 
                         (PyExtTypeNameGen(
                            ns=self.name,compressed=True,
                            is_pytype=True,is_pydecl=True,is_ret=True).gen(t), name))
        
        self.pyx.println("cpdef %s get%s(self):" % 
                         (PyExtTypeNameGen(
                            ns=self.name,compressed=True,
                            is_pytype=True,is_pydecl=True,is_ret=True).gen(t), name))
        self.pyx.inc_indent()
        self.pyx.println("return dynamic_cast[%s_decl.I%sP](self._hndl).get%s()" % 
                         (self.name, self.clsname, name))
        self.pyx.dec_indent()

        # Generate a non-const accessor
        self.decl_pxd.println("void set" + name + "(" +
            self.decl_pxd_ptr_tgen.gen(t) + " v)")

        print("<-- gen_enum_accessors %s" % self.field.name)

   
    def gen_scalar_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.decl_pxd.println(
            self.decl_pxd_ptr_tgen.gen(t) + " get" + name + "()")
        self.decl_pxd.println()
        
        
        self.pxd.println("cpdef %s get%s(self)" % 
                         (PyExtTypeNameGen(ns=self.name,compressed=True,is_ret=True).gen(t), name))
        
        self.pyx.println("cpdef %s get%s(self):" % 
                         (PyExtTypeNameGen(ns=self.name,compressed=True,is_ret=True).gen(t), name))
        self.pyx.inc_indent()
        self.pyx.println("return dynamic_cast[%s_decl.I%sP](self._hndl).get%s()" % 
                         (self.name, self.clsname, name))
        self.pyx.dec_indent()

        # Generate a non-const accessor
        self.decl_pxd.println("void set" + name + "(" +
            self.decl_pxd_ptr_tgen.gen(t) + " v)")

    def gen_rawptr_accessors(self, t):
        # Generate a read-only accessor
        name = self.field.name[0].upper() + self.field.name[1:]
        self.decl_pxd.println(self.decl_pxd_ptr_tgen.gen(t) + 
            "get" + name + "();")
        self.decl_pxd.println()

        # Generate a setter
        self.decl_pxd.println("void set" + name + "(" +
            self.decl_pxd_ptr_tgen.gen(t) + "v)")

    def gen_uptr_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.decl_pxd.println(self.decl_pxd_ptr_tgen.gen(t.t) + 
            "get" + name + "()")
        self.decl_pxd.println()

        # Generate a setter
        self.decl_pxd.println("void set" + name + "(" + self.decl_pxd_ptr_tgen.gen(t.t) + "v)")

    def gen_sptr_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.decl_pxd.println(
            PyExtTypeNameGen(ns=self.name,compressed=True,is_pydecl=True).gen(t) + " get" + name + "()")
        self.decl_pxd.println()

        # Generate a setter
        self.decl_pxd.println("void set" + name + "(" +
            PyExtTypeNameGen(ns=self.name,compressed=True,is_pydecl=True).gen(t) + " v)")

    def gen_string_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.decl_pxd.println(
            PyExtTypeNameGen(ns=self.name,compressed=True,is_ref=True,is_const=True).gen(t) + 
            "get" + name + "()")
        self.decl_pxd.println()

        self.pxd.println("cpdef %s get%s(self)" % (
            PyExtTypeNameGen(ns=self.name,compressed=True,is_ref=False,is_const=False).gen(t),
            name))
        self.pyx.println("cpdef %s get%s(self):" % (
            PyExtTypeNameGen(ns=self.name,compressed=True,is_ref=False,is_const=False).gen(t),
            name))
        self.pyx.inc_indent()
        self.pyx.println("return dynamic_cast[%s_decl.I%sP](self._hndl).get%s()" %
                         (self.name, self.clsname, name))
        self.pyx.dec_indent()

        # Generate a setter
        self.decl_pxd.println("void set_" + self.field.name + "(" +
            PyExtTypeNameGen(ns=self.name,compressed=True,is_const=True,is_ref=True).gen(t) + "v)")

    def const_ref_ret(self, t, is_pydecl=False, is_pytype=False):
        return PyExtTypeNameGen(ns=self.name,compressed=True,is_pydecl=is_pydecl,
                                is_pytype=is_pytype, is_ret=True,is_const=True).gen(t)
    
    def nonconst_ref_ret(self, t, is_pydecl=False, is_pytype=False):
        return PyExtTypeNameGen(ns=self.name,compressed=True,is_pydecl=is_pydecl, is_pytype=is_pytype,
                                is_ret=True,is_const=False).gen(t)
    
    