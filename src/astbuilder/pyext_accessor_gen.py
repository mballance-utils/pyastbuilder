from astbuilder.pyext_type_name_gen import PyExtTypeNameGen
from astbuilder.type_pointer import PointerKind
from astbuilder.type_scalar import TypeKind
from astbuilder.visitor import Visitor


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
    
    def __init__(self, name, clsname, pxd, pyx):
        super().__init__()
        self.name = name
        self.clsname = clsname
        self.pxd = pxd
        self.pyx = pyx
        self.field = None
        
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

    def visitTypeScalar(self, t):
        if t.t == TypeKind.String:
            self.gen_string_accessors(t)
        else:
            self.gen_scalar_accessors(t)
    
    def gen_collection_accessors(self, t):
        # Generate a read-only accessor
#        self.pxd.println(self.const_ref_ret(t) + "get_" + self.field.name + "()")
#        self.pxd.println()

        # Generate a non-const accessor
        self.pxd.println(self.nonconst_ref_ret(t) + "get_" + self.field.name + "();")
        
#         self.pyx.println("cdef %s get_%s():" % (self.nonconst_ref_ret(t), self.field.name))
#         self.pyx.inc_indent()
#         self.pyx.println("return (<%s_decl.%s *>self.thisptr).get_%s()" %
#                          (self.name, self.clsname, self.field.name))
#         self.pyx.dec_indent()

   
    def gen_scalar_accessors(self, t):
        # Generate a read-only accessor
        self.pxd.println(
            PyExtTypeNameGen(compressed=True,is_ret=True).gen(t) + 
            " get_" + self.field.name + "()")
        self.pxd.println()
        
        self.pyx.println("cdef %s get_%s(self):" % 
                         (PyExtTypeNameGen(compressed=True,is_ret=True).gen(t), self.field.name))
        self.pyx.inc_indent()
        self.pyx.println("return (<%s_decl.%s *>self.thisptr).get_%s()" % 
                         (self.name, self.clsname, self.field.name))
        self.pyx.dec_indent()

        # Generate a non-const accessor
        self.pxd.println("void set_" + self.field.name + "(" +
            PyExtTypeNameGen(compressed=True,is_ret=False).gen(t) + " v)")

    def gen_rawptr_accessors(self, t):
        # Generate a read-only accessor
        self.pxd.println(
            PyExtTypeNameGen(compressed=True,is_ref=False,is_const=False).gen(t) + 
            "get_" + self.field.name + "();")
        self.pxd.println()

        # Generate a setter
        self.pxd.println("void set_" + self.field.name + "(" +
            PyExtTypeNameGen(compressed=True,is_const=False,is_ref=False).gen(t) + "v)")

    def gen_uptr_accessors(self, t):
        # Generate a read-only accessor
        self.pxd.println(
            PyExtTypeNameGen(compressed=True,is_ptr=True,is_const=False).gen(t.t) + 
            "get_" + self.field.name + "()")
        self.pxd.println()

        # Generate a setter
        self.pxd.println("void set_" + self.field.name + "(" +
            PyExtTypeNameGen(compressed=True,is_const=False,is_ptr=True).gen(t.t) + "v)")

    def gen_sptr_accessors(self, t):
        # Generate a read-only accessor
        self.pxd.println(
            PyExtTypeNameGen(compressed=True).gen(t) + " get_" + 
            self.field.name + "()")
        self.pxd.println()

        # Generate a setter
        self.pxd.println("void set_" + self.field.name + "(" +
            PyExtTypeNameGen(compressed=True).gen(t) + " v)")

    def gen_string_accessors(self, t):
        # Generate a read-only accessor
        self.pxd.println(
            PyExtTypeNameGen(compressed=True,is_ref=True,is_const=True).gen(t) + 
            "get_" + self.field.name + "()")
        self.pxd.println()

        self.pyx.println("cdef %s get_%s(self):" % (
            PyExtTypeNameGen(compressed=True,is_ref=False,is_const=False).gen(t),
            self.field.name))
        self.pyx.inc_indent()
        self.pyx.println("return (<%s_decl.%s *>self.thisptr).get_%s()" %
                         (self.name, self.clsname, self.field.name))
        self.pyx.dec_indent()

        # Generate a setter
        self.pxd.println("void set_" + self.field.name + "(" +
            PyExtTypeNameGen(compressed=True,is_const=True,is_ref=True).gen(t) + "v)")

    def const_ref_ret(self, t):
        return PyExtTypeNameGen(compressed=True,is_ret=True,is_const=True).gen(t)
    
    def nonconst_ref_ret(self, t):
        return PyExtTypeNameGen(compressed=True,is_ret=True,is_const=False).gen(t)
    
    