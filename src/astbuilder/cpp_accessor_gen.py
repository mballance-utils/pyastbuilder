
from .ast_enum import AstEnum
from .ast_flags import AstFlags
from .ast_struct import AstStruct
from astbuilder.visitor import Visitor
from astbuilder.cpp_type_name_gen import CppTypeNameGen
from astbuilder.type_scalar import TypeKind
from astbuilder.type_pointer import PointerKind

class CppAccessorGen(Visitor):
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
    
    def __init__(self, out_h, out_ih, out_cpp, clsname):
        super().__init__()
        self.out_h = out_h
        self.out_ih = out_ih
        self.out_cpp = out_cpp
        self.clsname = clsname
        self.field = None
        
    def gen(self, field):
        self.field = field

        print("GenAccessor: %s=%s" % (self.field.name, str(self.field.t)))
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

    def visitTypeUserDef(self, t):
        print("GenAccessor: UserDef %s" % str(t.target))
        if isinstance(t.target, AstStruct):
            self.decl_struct_accessor(t)
        elif isinstance(t.target, (AstEnum,AstFlags)):
            self.gen_scalar_accessors(t)

    def decl_struct_accessor(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.out_h.println(
            "virtual " + 
            CppTypeNameGen(compressed=True,is_ret=True,is_ref=True,is_const=True).gen(t) + 
            "get" + name + "() const override;")
        self.out_ih.println(
            "virtual " + 
            CppTypeNameGen(compressed=True,is_ret=True,is_ref=True,is_const=True).gen(t) + 
            "get" + name + "() const = 0;")
        self.out_h.println()
        self.out_ih.println()

        self.out_cpp.println(
            CppTypeNameGen(compressed=True,is_ret=True,is_ref=True,is_const=True).gen(t) + 
                             self.clsname + "::get" + name + "() const {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("return m_" + self.field.name + ";")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")
        self.out_cpp.println()
        
        # Generate a non-const accessor
        self.out_h.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True,is_ret=False,is_ref=True,is_const=True).gen(t) + "v) override;")
        self.out_ih.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True,is_ret=False,is_ref=True,is_const=True).gen(t) + "v) = 0;")

        self.out_cpp.println("void " + self.clsname + "::set" + name + 
                "(" + CppTypeNameGen(compressed=True,is_ret=False,is_ref=True,is_const=True).gen(t) + "v) {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("m_" + self.field.name + " = v;")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")
    
    def gen_collection_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.out_h.println("virtual " + self.const_ref_ret(t) + "get" + name + "() const override;")
        self.out_ih.println("virtual " + self.const_ref_ret(t) + "get" + name + "() const = 0;")
        self.out_h.println()
        self.out_ih.println()

        self.out_cpp.println(self.const_ref_ret(t) + 
                             self.clsname + "::get" + name + "() const {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("return m_" + self.field.name + ";")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")
        self.out_cpp.println()
        
        # Generate a non-const accessor
        self.out_h.println("virtual " + self.nonconst_ref_ret(t) + "get" + name + "() override;")
        self.out_ih.println("virtual " + self.nonconst_ref_ret(t) + "get" + name + "() = 0;")

        self.out_cpp.println(self.nonconst_ref_ret(t) + 
                             self.clsname + "::get" + name + "() {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("return m_" + self.field.name + ";")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")        
   
    def gen_scalar_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.out_h.println(
            "virtual " + 
            CppTypeNameGen(compressed=True,is_ret=True).gen(t) + 
            " get" + name + "() const override;")
        self.out_ih.println(
            "virtual " + 
            CppTypeNameGen(compressed=True,is_ret=True).gen(t) + 
            " get" + name + "() const = 0;")
        self.out_h.println()
        self.out_ih.println()

        self.out_cpp.println(
            CppTypeNameGen(compressed=True,is_ret=True).gen(t) + 
                             " " + self.clsname + "::get" + name + "() const {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("return m_" + self.field.name + ";")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")
        self.out_cpp.println()
        
        # Generate a non-const accessor
        self.out_h.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True,is_ret=False).gen(t) + " v) override;")
        self.out_ih.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True,is_ret=False).gen(t) + " v) = 0;")

        self.out_cpp.println("void " + self.clsname + "::set" + name + 
                "(" + CppTypeNameGen(compressed=True,is_ret=False).gen(t) + " v) {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("m_" + self.field.name + " = v;")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")
        
    def gen_rawptr_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.out_h.println("virtual " + 
            CppTypeNameGen(compressed=True,is_ref=False,is_const=False).gen(t) + 
            "get" + name + "() override;")
        self.out_ih.println("virtual " + 
            CppTypeNameGen(compressed=True,is_ref=False,is_const=False).gen(t) + 
            "get" + name + "() = 0;")
        self.out_h.println()
        self.out_ih.println()

        self.out_cpp.println(
            CppTypeNameGen(compressed=True,is_const=False,is_ref=False).gen(t) + 
                            self.clsname + "::get" + name + "() {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("return m_" + self.field.name + ";")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")
        self.out_cpp.println()
        
        # Generate a setter
        self.out_h.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True,is_const=False,is_ref=False).gen(t) + "v) override;")
        self.out_ih.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True,is_const=False,is_ref=False).gen(t) + "v) = 0;")

        self.out_cpp.println("void " + self.clsname + "::set" + name + 
                "(" + CppTypeNameGen(compressed=True,is_const=False,is_ref=False).gen(t) + "v) {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("m_" + self.field.name + " = v;")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}") 
                       
    def gen_uptr_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.out_h.println("virtual " +
            CppTypeNameGen(compressed=True,is_ptr=True,is_const=False).gen(t.t) + 
            "get" + name + "() const override;")
        self.out_ih.println("virtual " + 
            CppTypeNameGen(compressed=True,is_ptr=True,is_const=False).gen(t.t) + 
            "get" + name + "() const = 0;")
        self.out_h.println()
        self.out_ih.println()

        self.out_cpp.println(
            CppTypeNameGen(compressed=True,is_ptr=True,is_const=False).gen(t.t) + 
                            self.clsname + "::get" + name + "() const {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("return m_" + self.field.name + ".get();")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")
        self.out_cpp.println()
        
        # Generate a setter
        self.out_h.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True,is_const=False,is_ptr=True).gen(t.t) + "v) override;")
        self.out_ih.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True,is_const=False,is_ptr=True).gen(t.t) + "v) = 0;")

        self.out_cpp.println("void " + self.clsname + "::set" + name + 
                "(" + CppTypeNameGen(compressed=True,is_const=False,is_ptr=True).gen(t.t) + "v) {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("m_" + self.field.name + " = " + 
            CppTypeNameGen(compressed=True).gen(t) + "(v);")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")

    def gen_sptr_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.out_h.println("virtual " + 
            CppTypeNameGen(compressed=True).gen(t) + " get" + name + "() const override;")
        self.out_ih.println("virtual " + 
            CppTypeNameGen(compressed=True).gen(t) + " get" + name + "() const = 0;")
        self.out_h.println()
        self.out_ih.println()

        self.out_cpp.println(
            CppTypeNameGen(compressed=True).gen(t) + 
                            " " + self.clsname + "::get" + name + "() const {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("return m_" + self.field.name + ";")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")
        self.out_cpp.println()
        
        # Generate a setter
        self.out_h.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True).gen(t) + " v) override;")
        self.out_ih.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True).gen(t) + " v) = 0;")

        self.out_cpp.println("void " + self.clsname + "::set" + name + 
                "(" + CppTypeNameGen(compressed=True).gen(t) + " v) {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("m_" + self.field.name + " = v;")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")
                        
    def gen_string_accessors(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        
        # Generate a read-only accessor
        self.out_h.println("virtual " + 
            CppTypeNameGen(compressed=True,is_ref=True,is_const=True).gen(t) + 
            "get" + name + "() const override;")
        self.out_ih.println("virtual " + 
            CppTypeNameGen(compressed=True,is_ref=True,is_const=True).gen(t) + 
            "get" + name + "() const = 0;")
        self.out_h.println()
        self.out_ih.println()

        self.out_cpp.println(
            CppTypeNameGen(compressed=True,is_const=True,is_ref=True).gen(t) + 
                            self.clsname + "::get" + name + "() const {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("return m_" + self.field.name + ";")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")
        self.out_cpp.println()
        
        # Generate a setter
        self.out_h.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True,is_const=True,is_ref=True).gen(t) + "v) override;")
        self.out_ih.println("virtual void set" + name + "(" +
            CppTypeNameGen(compressed=True,is_const=True,is_ref=True).gen(t) + "v) = 0;")

        self.out_cpp.println("void " + self.clsname + "::set" + name + 
                "(" + CppTypeNameGen(compressed=True,is_const=True,is_ref=True).gen(t) + "v) {")
        self.out_cpp.inc_indent()
        self.out_cpp.println("m_" + self.field.name + " = v;")
        self.out_cpp.dec_indent()
        self.out_cpp.println("}")        
         
    def const_ref_ret(self, t):
        return CppTypeNameGen(compressed=True,is_ret=True,is_const=True).gen(t)
    
    def nonconst_ref_ret(self, t):
        return CppTypeNameGen(compressed=True,is_ret=True,is_const=False).gen(t)
    
    
