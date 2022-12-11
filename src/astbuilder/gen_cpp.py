'''
Created on Sep 12, 2020

@author: ballance
'''
import os
import shutil

from astbuilder.ast import Ast
from astbuilder.ast_class import AstClass
from astbuilder.ast_enum import AstEnum
from astbuilder.ast_flags import AstFlags
from .ast_struct import AstStruct
from astbuilder.gen_cpp_visitor import GenCppVisitor
from astbuilder.outstream import OutStream
from astbuilder.type_list import TypeList
from astbuilder.type_pointer import TypePointer, PointerKind
from astbuilder.type_scalar import TypeScalar, TypeKind
from astbuilder.type_userdef import TypeUserDef
from astbuilder.visitor import Visitor

from .cpp_type_name_gen import CppTypeNameGen
from astbuilder.cpp_accessor_gen import CppAccessorGen
from astbuilder.type_map import TypeMap
from astbuilder.cpp_gen_ns import CppGenNS
from astbuilder.cpp_gen_factory import CppGenFactory


class GenCPP(Visitor):
    
    def __init__(self, 
                 outdir, 
                 name,
                 license,
                 namespace):
        self.outdir = outdir
        self.name = name
        self.license = license
        self.namespace = namespace
        
        if license is not None:
            with open(license, "r") as f:
                self.license = f.read()
        self.enum_t = set()
        pass
    
    def generate(self, ast):
        # Collect the set of enumerated-type names
        for e in ast.enums:
            self.enum_t.add(e.name)
            
        CppGenFactory(
            self.outdir,
            self.license,
            self.namespace).gen(ast)
            
        ast.accept(self)
        GenCppVisitor(
            self.outdir, 
            self.license,
            self.namespace).generate(ast)
        
        with open(os.path.join(self.outdir, "CMakeLists.txt"), "w") as f:
            f.write(self.gen_cmake(ast))
    
    def visitAstClass(self, c : AstClass):
        h = OutStream()
        inc_h = OutStream()
        cpp = OutStream()
        
        self.define_class(c, h, inc_h, cpp)
        
#        h = self.define_class_h(c)
#        cpp = self.define_class_cpp(c)

        incdir = CppGenNS.incdir(self.outdir, self.namespace)
        
        if not os.path.isdir(self.outdir):
            os.makedirs(self.outdir)
            
        with open(os.path.join(self.outdir, c.name + ".h"), "w") as f:
            f.write(h.content())
            
        with open(os.path.join(self.outdir, c.name + ".cpp"), "w") as f:
            f.write(cpp.content())
            
        with open(os.path.join(incdir, "I%s.h" % c.name), "w") as f:
            f.write(inc_h.content())

    def visitAstStruct(self, s):
        h = OutStream()

        self.define_struct(s, h)

        incdir = CppGenNS.incdir(self.outdir, self.namespace)

        if not os.path.isdir(self.outdir):
            os.makedirs(self.outdir)

        with open(os.path.join(incdir, "%s.h" % s.name), "w") as f:
            f.write(h.content())

    def visitAstEnum(self, e:AstEnum):
        out_h = OutStream()
        out_h.println("/****************************************************************************")
        out_h.println(" * " + e.name + ".h")
        if self.license is not None:
            out_h.write(self.license)
        out_h.println(" ****************************************************************************/")
        out_h.println("#pragma once")
        out_h.println()

        CppGenNS.enter(self.namespace, out_h)        
        
        out_h.println("enum class " + e.name + " {")
        out_h.inc_indent()
        
        for v in e.values:
            out_h.println(v[0] + ",")
        out_h.dec_indent()
        out_h.println("};")

        CppGenNS.leave(self.namespace, out_h)        
        
        incdir = CppGenNS.incdir(self.outdir, self.namespace)
        
        with open(os.path.join(incdir, e.name + ".h"), "w") as f:
            f.write(out_h.content())

    def visitAstFlags(self, f:AstFlags):
        out_h = OutStream()
        out_h.println("/****************************************************************************")
        out_h.println(" * " + f.name + ".h")
        if self.license is not None:
            out_h.write(self.license)
        out_h.println(" ****************************************************************************/")
        out_h.println("#pragma once")
        out_h.println("#include <stdint.h>")
        out_h.println()

        CppGenNS.enter(self.namespace, out_h)
        
        out_h.println("enum class " + f.name + " {")

        out_h.inc_indent()
        out_h.println("NoFlags = 0,")
        for i,v in enumerate(f.values):
            if i+1 < len(f.values):
                out_h.println(v + " = (1 << " + str(i) + "),")
            else:
                out_h.println(v + " = (1 << " + str(i) + ")")
        out_h.dec_indent()

        out_h.println("};")
        out_h.println()

        out_h.println("static inline %s operator | (const %s lhs, const %s rhs) {" % (
            f.name, f.name, f.name))
        out_h.inc_indent()
        out_h.println("return static_cast<%s>(static_cast<uint32_t>(lhs) | static_cast<uint32_t>(rhs));" % (
            f.name))
        out_h.dec_indent()
        out_h.println("}")
        out_h.println()

        out_h.println("static inline %s operator |= (%s &lhs, const %s rhs) {" % (
            f.name, f.name, f.name))
        out_h.inc_indent()
        out_h.println("lhs = static_cast<%s>(static_cast<uint32_t>(lhs) | static_cast<uint32_t>(rhs));" % (
            f.name))
        out_h.println("return lhs;")
        out_h.dec_indent()
        out_h.println("}")
        out_h.println()

        out_h.println("static inline %s operator & (const %s lhs, const %s rhs) {" % (
            f.name, f.name, f.name))
        out_h.inc_indent()
        out_h.println("return static_cast<%s>(static_cast<uint32_t>(lhs) & static_cast<uint32_t>(rhs));" % f.name)
        out_h.dec_indent()
        out_h.println("}")
        out_h.println()

        out_h.println("static inline %s operator ~ (const %s lhs) {" % (f.name, f.name))
        out_h.inc_indent()
        out_h.println("return static_cast<%s>(~static_cast<uint32_t>(lhs));" % f.name)
        out_h.dec_indent()
        out_h.println("}")
        out_h.println()

        CppGenNS.leave(self.namespace, out_h)        
        
        incdir = CppGenNS.incdir(self.outdir, self.namespace)
        with open(os.path.join(incdir, f.name + ".h"), "w") as fp:
            fp.write(out_h.content())
            
    def define_class(self, c, out_h, out_inc_h, out_cpp):
        # Class body output stream
        out_cls = OutStream()
        out_icls = OutStream()

        #************************************************************
        #* Beginning of the header file        
        #************************************************************
        out_h.println("/****************************************************************************")
        out_inc_h.println("/****************************************************************************")
        out_h.println(" * " + c.name + ".h")
        out_inc_h.println(" * I" + c.name + ".h")
        if self.license is not None:
            out_h.write(self.license)
            out_inc_h.write(self.license)
        out_h.println(" ****************************************************************************/")
        out_inc_h.println(" ****************************************************************************/")
        out_h.println("#pragma once")
        out_inc_h.println("#pragma once")
        out_h.println("#include <stdint.h>")
        out_inc_h.println("#include <stdint.h>")
        out_h.println("#include <map>")
        out_inc_h.println("#include <map>")
        out_h.println("#include <memory>")
        out_inc_h.println("#include <memory>")
        out_h.println("#include <set>")
        out_inc_h.println("#include <set>")
        out_h.println("#include <string>")
        out_inc_h.println("#include <string>")
        out_h.println("#include <vector>")
        out_inc_h.println("#include <vector>")
        out_h.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "IVisitor.h"))
        out_inc_h.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "IVisitor.h"))
        out_h.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "I%s.h" % c.name))

        # if self.namespace is not None:
        #     out_h.println("#include \"%s/I%s.h\"" % (self.namespace, c.name))
        # else:
        #     out_h.println("#include \"I%s.h\"" % c.name)
            
        if c.super is not None:
            out_h.println("#include \"" + c.super.name + ".h\"")
            out_inc_h.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "I%s.h"%c.super.name))
            out_h.println()
            out_inc_h.println()
        for key,d in c.deps.items():
            if isinstance(d.target, (AstEnum,AstFlags,AstStruct)):
                out_icls.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "%s.h"%key))
#                out_h.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "%s.h"%key))

        CppGenNS.enter(self.namespace, out_cls)
        CppGenNS.enter(self.namespace, out_icls)

        # Handle dependencies
        for key,d in c.deps.items():
            if isinstance(d.target, AstClass):
                out_cls.println("class I" + key + ";")
                out_icls.println("class I" + key + ";")
                out_cls.println("typedef std::unique_ptr<I" + key + "> I" + key + "UP;")
                out_icls.println("typedef std::unique_ptr<I" + key + "> I" + key + "UP;")
                out_cls.println("typedef std::shared_ptr<I" + key + "> I" + key + "SP;")
                out_icls.println("typedef std::shared_ptr<I" + key + "> I" + key + "SP;")
            elif isinstance(d.target, (AstEnum,AstStruct,AstFlags)):
                pass
            else:
                raise Exception("Unknown ref " + str(d.target))

        out_cls.println("class " + c.name + ";")
        out_icls.println("class I" + c.name + ";")
        out_cls.println("typedef std::unique_ptr<" + c.name + "> " + c.name + "UP;")
        out_icls.println("typedef std::unique_ptr<I" + c.name + "> I" + c.name + "UP;")
        out_cls.println("typedef std::shared_ptr<" + c.name + "> " + c.name + "SP;")
        out_icls.println("typedef std::shared_ptr<I" + c.name + "> I" + c.name + "SP;")
        out_cls.println()
        out_icls.println()
        out_cls.println("#ifdef _WIN32")
        out_cls.println("#ifdef DLLEXPORT")
        out_cls.println("__declspec(dllexport)")
        out_cls.println("#endif")
        out_cls.println("#endif /* _WIN32 */")
        out_cls.write("class " + c.name)
        out_icls.write("class I" + c.name)

        out_cls.write(" : public virtual I%s" % c.name)        
        if c.super is not None:
            out_cls.write(", public %s" % c.super.name)
            out_icls.write(" : public virtual I%s" % c.super.name)
        out_cls.write(" {\n")
        out_icls.write(" {\n")
        out_cls.write("public:\n")
        out_icls.write("public:\n")
        out_cls.inc_indent()
        out_icls.inc_indent()
        
        # Constructor (only in actual class)
        out_cls.println(c.name + "(");
        out_cls.inc_indent()
        self.gen_ctor_params(c, out_cls)
        out_cls.println(");");
        out_cls.dec_indent()

        # Destructor (in both)        
        out_cls.println();
        out_icls.println();
        out_cls.println("virtual ~" + c.name + "();");
        out_icls.println("virtual ~I" + c.name + "() { }");
        out_cls.println();
        out_icls.println();
        
            
#             # Const accessor
#             out_cls.println(
#                 CppTypeNameGen(compressed=True,is_ret=True,is_const=True).gen(f.t) + " " + f.name + "() const {")
#             out_cls.inc_indent()
#             # Return the raw pointer held by a unique pointer. Return everything else by value
#             if isinstance(f.t, TypePointer) and f.t.pt == PointerKind.Unique:
#                 out_cls.println("return m_" + f.name + ".get();")
#             else:
#                 out_cls.println("return m_" + f.name + ";")
#             out_cls.dec_indent()
#             out_cls.println("}")
#             
#             # Non-const accessor
#             out_cls.println(
#                 CppTypeNameGen(compressed=True,is_ret=True,is_const=False).gen(f.t) + " " + f.name + "() {")
#             out_cls.inc_indent()
#             # Return the raw pointer held by a unique pointer. Return everything else by value
#             if isinstance(f.t, TypePointer) and f.t.pt == PointerKind.Unique:
#                 out_cls.println("return m_" + f.name + ".get();")
#             else:
#                 out_cls.println("return m_" + f.name + ";")
#             out_cls.dec_indent()
#             out_cls.println("}")
# 
#             # TODO: Generate an accessor for adding list elements            
#             # TODO: Generate an accessor for accessing individual elements            
            

            

        #************************************************************
        #* Beginning of the C++ file        
        #************************************************************
        out_cpp.println("/****************************************************************************")
        out_cpp.println(" * " + c.name + ".cpp")
        if self.license is not None:
            out_cpp.write(self.license)
        out_cpp.println(" ****************************************************************************/")
        out_cpp.println("#include \"" + c.name + ".h\"")
        out_cpp.println()
        # Include files needed for circular dependencies
        for key,d in c.deps.items():
            # Other types (eg enums) will have already been included
            if isinstance(d.target, AstClass):
                out_cpp.println("#include \"" + key + ".h\"")
                
        out_cpp.println()

        CppGenNS.enter(self.namespace, out_cpp)        
            
        out_cpp.println(c.name + "::" + c.name + "(")
        
        out_cpp.inc_indent()
        self.gen_ctor_params(c, out_cpp)
        out_cpp.write(")")
        self.gen_ctor_init(c, out_cpp)
        out_cpp.dec_indent()
        
        out_cpp.println("{\n")
 

        # Assign fields that are non-parameter and have defaults            
        out_cpp.inc_indent()
        for d in filter(lambda d:d.init is not None, c.data):
            out_cpp.println("m_" + d.name + " = " + d.init + ";")
        out_cpp.dec_indent()
            
        # TODO: assignments
        out_cpp.println("}")
        out_cpp.println()
        out_cpp.println(c.name + "::~" + c.name + "() {")
        out_cpp.println()
        out_cpp.println("}")
        
        # Field accessors. Content goes both in .h and .cpp files
        out_cpp.println()
        out_cls.println()
        out_icls.println()
        
        accessor_gen = CppAccessorGen(out_cls, out_icls, out_cpp, c.name)
        for i,f in enumerate(c.data):
            if i > 0:
                out_cls.println()
                out_icls.println()
                out_cpp.println()
            accessor_gen.gen(f)
            
        out_cls.println()
        out_cpp.println()


        # Wrap up class-content generation
        if c.super is None:
            out_icls.println("virtual void accept(IVisitor *v) = 0;")
        out_cls.println("virtual void accept(IVisitor *v) override { v->visit" + c.name + "(this);}")
        
        out_cls.dec_indent()
        out_cls.println();
        out_cls.println("private:\n")
        out_cls.inc_indent()
        for f in c.data:
            out_cls.println(CppTypeNameGen(True).gen(f.t) + " m_" + f.name + ";")
        out_cls.dec_indent()
        
        out_cls.write("};\n")
        out_icls.write("};\n")

        CppGenNS.leave(self.namespace, out_cls)
        CppGenNS.leave(self.namespace, out_icls)
        CppGenNS.leave(self.namespace, out_cpp)
                    
        out_h.write(out_cls.content())
        out_inc_h.write(out_icls.content())
                
        pass
        
    def define_class_h(self, c):
        out_cls = OutStream()
        
        out_h = OutStream()
        out_h.println("/****************************************************************************")
        out_h.println(" * " + c.name + ".h")
        if self.license is not None:
            out_h.write(self.license)
        out_h.println(" ****************************************************************************/")
        out_h.println("#pragma once")
        out_h.println("#include <stdint.h>")
        out_h.println("#include <map>")
        out_h.println("#include <memory>")
        out_h.println("#include <set>")
        out_h.println("#include <string>")
        out_h.println("#include <vector>")
        out_h.println("#include \"IVisitor.h\"")
        
        if c.super is not None:
            out_h.println("#include \"" + c.super.name + ".h\"")
            out_h.println()

        CppGenNS.enter(self.namespace, out_cls)
            
        # Handle dependencies
        for key,d in c.deps.items():
            if isinstance(d.target, AstClass):
                out_cls.println("class " + key + ";")
                out_cls.println("typedef std::unique_ptr<" + key + "> " + key + "UP;")
                out_cls.println("typedef std::shared_ptr<" + key + "> " + key + "SP;")
            elif isinstance(d.target, (AstEnum,AstFlags)):
                out_h.println("#include \"" + key + ".h\"")
            else:
                raise Exception("Unknown ref " + str(d.target))
#            if not d.circular:
#                out_h.println("#include \"" + key + ".h\"")
#            else:
#                raise Exception("TODO: handle circular dependency on " + key)

        out_cls.println("class " + c.name + ";")
        out_cls.println("typedef std::unique_ptr<" + c.name + "> " + c.name + "UP;")
        out_cls.println("typedef std::shared_ptr<" + c.name + "> " + c.name + "SP;")
        out_cls.println()
        out_cls.println("#ifdef _WIN32")
        out_cls.println("#ifdef DLLEXPORT")
        out_cls.println("__declspec(dllexport)")
        out_cls.println("#endif")
        out_cls.println("#endif /* _WIN32 */")
        out_cls.write("class " + c.name)
        
        if c.super is not None:
            out_cls.write(" : public " + c.super.name)
        out_cls.write(" {\n")
        out_cls.write("public:\n")
        out_cls.inc_indent()
        out_cls.println(c.name + "(");
        out_cls.inc_indent()
        self.gen_ctor_params(c, out_cls)
        out_cls.println(");");
        out_cls.dec_indent()
        
        out_cls.println();
        out_cls.println("virtual ~" + c.name + "();");
        out_cls.println();
        
        # Field accessors
        CppAccessorGen(out_cls, out_cpp)
        for f in c.data:
            # If the data is a collection (list, map), we need:
            # - const accessor
            # - non-const accessor
            #
            # If the data is scalar 

            
            # Const accessor
            out_cls.println(
                CppTypeNameGen(compressed=True,is_ret=True,is_const=True).gen(f.t) + " " + f.name + "() const {")
            out_cls.inc_indent()
            # Return the raw pointer held by a unique pointer. Return everything else by value
            if isinstance(f.t, TypePointer) and f.t.pt == PointerKind.Unique:
                out_cls.println("return m_" + f.name + ".get();")
            else:
                out_cls.println("return m_" + f.name + ";")
            out_cls.dec_indent()
            out_cls.println("}")
            out_cls.println()
            
            # Non-const accessor
            out_cls.println(
                CppTypeNameGen(compressed=True,is_ret=True,is_const=False).gen(f.t) + " " + f.name + "() {")
            out_cls.inc_indent()
            # Return the raw pointer held by a unique pointer. Return everything else by value
            if isinstance(f.t, TypePointer) and f.t.pt == PointerKind.Unique:
                out_cls.println("return m_" + f.name + ".get();")
            else:
                out_cls.println("return m_" + f.name + ";")
            out_cls.dec_indent()
            out_cls.println("}")
            out_cls.println()
            
            # Setter
            if not isinstance(f.t, (TypeList,TypeMap)):
                out_cls.println("void " + f.name + "(" + CppTypeNameGen(compressed=True,is_ret=True,is_const=False).gen(f.t) + " v);")
                out_cls.println()

            # TODO: Generate an accessor for adding list elements            
            # TODO: Generate an accessor for accessing individual elements            
            
        # Visitor call
        out_cls.println("virtual void accept(IVisitor *v) { v->visit" + c.name + "(this);}")
        
        out_cls.dec_indent()
        out_cls.println();
        out_cls.println("private:\n")
        out_cls.inc_indent()
        for f in c.data:
            out_cls.println(CppTypeNameGen(True).gen(f.t) + " m_" + f.name + ";")
        out_cls.dec_indent()
        
        
        out_cls.write("};\n")

        CppGenNS.leave(self.namespace, out_cls)        

        return (out_h.content() + 
                out_inc.content() +
                out_cls.content())
    
    def define_class_cpp(self, c):
        out_cpp = OutStream()
        out_cpp.println("/****************************************************************************")
        out_cpp.println(" * " + c.name + ".cpp")
        if self.license is not None:
            out_cpp.write(self.license)
        out_cpp.println(" ****************************************************************************/")
        out_cpp.println("#include \"" + c.name + ".h\"")
        out_cpp.println()
        # Include files needed for circular dependencies
        for key,d in c.deps.items():
            out_cpp.println("#include \"" + key + ".h\"")
                
        out_cpp.println()

        CppGenNS.enter(self.namespace, out_cpp)        
            
        out_cpp.println(c.name + "::" + c.name + "(")
        
        out_cpp.inc_indent()
        self.gen_ctor_params(c, out_cpp)
        out_cpp.write(")")
        self.gen_ctor_init(c, out_cpp)
        out_cpp.dec_indent()
        
        out_cpp.println("{\n")
 

        # Assign fields that are non-parameter and have defaults            
        out_cpp.inc_indent()
        for d in filter(lambda d:d.init is not None, c.data):
            out_cpp.println("m_" + d.name + " = " + d.init + ";")
        out_cpp.dec_indent()
            
        # TODO: assignments
        out_cpp.println("}")
        out_cpp.println()
        out_cpp.println(c.name + "::~" + c.name + "() {")
        out_cpp.println()
        out_cpp.println("}")
        
        for f in c.data:
            if not isinstance(f.t, (TypeList,TypeMap)):
            
                # Setter
                out_cpp.println("void " + c.name + ":: " + f.name + "(" + CppTypeNameGen(compressed=True,is_ret=True,is_const=False).gen(f.t) + 
                            " v) {")
                out_cpp.inc_indent()
             
                # Return the raw pointer held by a unique pointer. Return everything else by value
                if isinstance(f.t, TypePointer) and f.t.pt == PointerKind.Unique:
                    out_cpp.println("m_" + f.name + " = " + 
                                CppTypeNameGen(compressed=True).gen(f.t) + "(v);")
                else:
                    out_cpp.println("m_" + f.name + " = v;")
                out_cpp.dec_indent()
                out_cpp.println("}")
                out_cpp.println()        

        CppGenNS.leave(self.namespace, out_cpp)
        
        return out_cpp.content()
    
    def gen_ctor_params(self, c, out_cpp):
        """Returns True if this level (or a previous level) added content"""
        ret = False
        if c.super is not None:
            # Recurse first
            ret |= self.gen_ctor_params(c.super.target, out_cpp)
            
        params = list(filter(lambda d : d.is_ctor, c.data))
        for i,p in enumerate(params):
            if ret and i == 0:
                out_cpp.write(",\n")
            out_cpp.write(out_cpp.ind)
            out_cpp.write(CppTypeNameGen(compressed=True,is_ret=True).gen(p.t) + " ")
            out_cpp.write(p.name + (",\n" if i+1 < len(params) else ""))
            ret = True
        
        return ret
    
    def collect_super_params(self, c):
        if c.super is not None:
            params = self.collect_super_params(c.super.target)
        else:
            params = []
        params.extend(list(filter(lambda d : d.is_ctor, c.data)))
        
        return params
    
    def gen_ctor_init(self, c, out_cpp):
        # TODO: collect what must be passed to base type
        if c.super is not None:
            super_params = self.collect_super_params(c.super.target)
        else:
            super_params = []
        
        params = list(filter(lambda d : d.is_ctor, c.data))
        
        if len(super_params) > 0 or len(params) > 0:
            out_cpp.write(" : \n")
        out_cpp.inc_indent()
        
        if len(super_params) > 0:
            out_cpp.write(out_cpp.ind + c.super.target.name + "(")
            for i,p in enumerate(super_params):
                out_cpp.write(p.name + (", " if i+1<len(super_params) else ""))
            out_cpp.write(")")
            if len(params) > 0:
                out_cpp.write(",\n")
            
        
        # First, handle super-params
        
        for i,p in enumerate(params):
            out_cpp.println("m_" + p.name + "(" + p.name + ")" +
                    ("," if (i+1) < len(params) else ""))
        
        out_cpp.dec_indent()
        
#        if c.super is not None:
#            self.gen_ctor_init(c.super.target, out_cpp)
#        out_cpp.write(") :\n")
#         out_cpp.dec_indent()
#         
#         if len(params) == 0:
#             out_cpp.println(") {")
#         else:
#             out_cpp.inc_indent()
#             out_cpp.inc_indent()
#             for i,p in enumerate(params):
#                 out_cpp.println("m_" + p.name + "(" + p.name + ")" +
#                                 ("," if i+1 < len(params) else " {"))
#             out_cpp.dec_indent()
#             out_cpp.dec_indent()        

    def define_struct(self, s, h):
        h.println("/****************************************************************************")
        h.println(" * " + s.name + ".h")
        if self.license is not None:
            h.write(self.license)
        h.println(" ****************************************************************************/")
        h.println("#pragma once")
        h.println("#include <stdint.h>")
        h.println("#include <map>")
        h.println("#include <memory>")
        h.println("#include <set>")
        h.println("#include <string>")
        h.println("#include <vector>")
        h.println()

        CppGenNS.enter(self.namespace, h)

        h.println()
        h.println("struct %s {" % s.name)
        h.inc_indent()
        for f in s.data:
            if f.init is not None:
                h.println("%s %s = %s;" % (
                    CppTypeNameGen(True).gen(f.t),
                    f.name,
                    f.init))
            else:
                h.println(CppTypeNameGen(True).gen(f.t) + " " + f.name + ";")
        h.dec_indent()
        h.println("};")

        h.println()

        CppGenNS.leave(self.namespace, h)

        pass
    
    def gen_cmake(self, ast):
        out = OutStream()
        out.println("#****************************************************************************")
        out.println("#* CMakeLists.txt for " + self.name)
        out.println("#****************************************************************************")
        out.println()
        out.println("cmake_minimum_required (VERSION 3.11)")
        out.println()
        out.println("project (" + self.name + ")")
        out.println()
        out.println("file(GLOB_RECURSE " + self.name + "_SRC")
        out.inc_indent()
        out.println("\"*.h\"")
        out.println("\"*.cpp\"")
        out.dec_indent()
        out.println(")")
        out.println()
        out.println("set(CMAKE_CXX_STANDARD 14)")
        out.println()
        out.println("set(CompilerFlags")
        out.println("CMAKE_CXX_FLAGS")
        out.println("CMAKE_CXX_FLAGS_DEBUG")
        out.println("CMAKE_CXX_FLAGS_RELEASE")
        out.println("CMAKE_C_FLAGS")
        out.println("CMAKE_C_FLAGS_DEBUG")
        out.println("CMAKE_C_FLAGS_RELEASE")
        out.println(")")
        out.println("foreach(CompilerFlag ${CompilerFlags})")
        out.println("string(REPLACE \"/MD\" \"/MT\" ${CompilerFlag} \"${${CompilerFlag}}\")")
        out.println("string(REPLACE \"/MDd\" \"/MTd\" ${CompilerFlag} \"${${CompilerFlag}}\")")
        out.println("endforeach()")
        out.println()
        out.println("if (CMAKE_CXX_COMPILER_ID STREQUAL \"GNU\")")
        out.println("add_compile_options(-fPIC)")
        out.println("endif()")
        out.println()
        out.println("add_library(" + self.name + " ${" + self.name + "_SRC})")
        out.println()
        out.println("target_include_directories(%s PUBLIC" % self.name)
        out.println("    ${PROJECT_SOURCE_DIR}/include")
        out.println(")")
        out.println()
        out.println("install(TARGETS " + self.name + "")
        out.inc_indent()
        out.println("DESTINATION lib")
        out.println("EXPORT " + self.name + "-targets)")
        out.dec_indent()
        out.println()
        out.println("install(DIRECTORY \"${PROJECT_SOURCE_DIR}/\"")
        out.inc_indent()
        out.println("DESTINATION \"include/" + self.name + "\"")
        out.println("COMPONENT dev")
        out.println("FILES_MATCHING PATTERN \"*.h\")")
        out.dec_indent()
        out.println()
        
        return out.content()
        
    
class FieldForwardRefGen(Visitor):
       
    def __init__(self, ast):
        self.ast = ast
        self.out = OutStream()
        self.seen = set()
    
    def gen(self, c):
        c.accept(self)
        return self.out.content()
    
    def visitTypePointer(self, t : TypePointer):
        Visitor.visitTypePointer(self, t)
        if t.pt == PointerKind.Shared or t.pt == PointerKind.Unique:
            self.out.write(self.out.ind + "typedef ")
            self.out.write(CppTypeNameGen().gen(t))
            self.out.write(" " + GetPointerType().gen(t) + 
                           "UP" if t.pt == PointerKind.Unique else "SP")
            self.out.write(";\n")
            
#            if t.pt == PointerKind.Shared:
#                self.out.write(" " + t.self.)
#            else:

    def visitTypeUserDef(self, t : TypeUserDef):
        if t.name not in self.seen:
            self.seen.add(t.name)
            if t.name in self.enum_t:
                self.out.println("enum " + t.name + ";")
            else:
                self.out.println("class " + t.name + ";")
                
class FieldIncludeGen(Visitor):
       
    def __init__(self):
        self.out = OutStream()
        self.seen = set()
    
    def gen(self, c):
        c.accept(self)
        return self.out.content()

    def visitTypeUserDef(self, t : TypeUserDef):
        if t.name not in self.seen:
            self.seen.add(t.name)
            self.out.println("#include \"" + t.name + ".h\"")           


        
class GetPointerType(Visitor):
    def __init__(self):
        self.out = ""
        
    def gen(self, t):
        t.accept(self)
        return self.out
    
    def visitTypeUserDef(self, t):
        self.out += t.name
        
