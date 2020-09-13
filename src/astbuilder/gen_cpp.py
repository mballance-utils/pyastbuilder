'''
Created on Sep 12, 2020

@author: ballance
'''
import os
import shutil

from astbuilder.ast import Ast
from astbuilder.ast_class import AstClass
from astbuilder.ast_enum import AstEnum
from astbuilder.gen_cpp_visitor import GenCppVisitor
from astbuilder.outstream import OutStream
from astbuilder.type_list import TypeList
from astbuilder.type_pointer import TypePointer, PointerKind
from astbuilder.type_scalar import TypeScalar, TypeKind
from astbuilder.type_userdef import TypeUserDef
from astbuilder.visitor import Visitor


class GenCPP(Visitor):
    
    def __init__(self, 
                 outdir, 
                 license,
                 namespace):
        self.outdir = outdir
        self.license = None
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
            
        ast.accept(self)
        GenCppVisitor(self.outdir, self.license).generate(ast)
        
        with open(os.path.join(self.outdir, "CMakeLists.txt"), "w") as f:
            f.write(self.gen_cmake(ast))
    
    def visitAstClass(self, c : AstClass):
        h = self.define_class_h(c)
        cpp = self.define_class_cpp(c)
        
        if not os.path.isdir(self.outdir):
            os.makedirs(self.outdir)

        with open(os.path.join(self.outdir, c.name + ".h"), "w") as f:
            f.write(h)
            
        with open(os.path.join(self.outdir, c.name + ".cpp"), "w") as f:
            f.write(cpp)
            
    def visitAstEnum(self, e:AstEnum):
        out_h = OutStream()
        out_h.println("/****************************************************************************")
        out_h.println(" * " + e.name + ".h")
        if self.license is not None:
            out_h.write(self.license)
        out_h.println(" ****************************************************************************/")
        out_h.println("#pragma once")
        out_h.println()
        
        if self.namespace is not None:
            out_h.println("namespace " + self.namespace + " {")
        
        out_h.println("enum " + e.name + " {")
        out_h.inc_indent()
        
        for v in e.values:
            out_h.println(v[0] + ",")
        out_h.dec_indent()
        out_h.println("};")
        
        if self.namespace is not None:
            out_h.println()
            out_h.println("} /* namespace " + self.namespace + " */")
        
        with open(os.path.join(self.outdir, e.name + ".h"), "w") as f:
            f.write(out_h.content())
            
        
    def define_class_h(self, c):
        out_inc = OutStream()
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
            out_h.println("#include \"" + c.super + ".h\"")
            out_h.println()

        # Handle dependencies
        for key,d in c.deps.items():
            if not d.circular:
                out_h.println("#include \"" + key + ".h\"")
            else:
                raise Exception("TODO: handle circular dependency on " + key)

        if self.namespace is not None:
            out_cls.println()
            out_cls.println("namespace " + self.namespace + " {")
            out_cls.println()
        

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
            out_cls.write(" : public " + c.super)
        out_cls.write(" {\n")
        out_cls.write("public:\n")
        out_cls.inc_indent()
        out_cls.println(c.name + "(");
        out_cls.inc_indent()
        params = list(filter(lambda d : d.is_ctor, c.data))
        for i,p in enumerate(params):
            out_cls.println(
                TypeNameGen(compressed=True,is_ret=True).gen(p.t) + " " + p.name + 
                    ("," if i+1 < len(params) else ""))
        out_cls.println(");");
        out_cls.dec_indent()
        
        out_cls.println();
        out_cls.println("virtual ~" + c.name + "();");
        out_cls.println();
        
        # Field accessors
        for f in c.data:
            out_cls.println(
                TypeNameGen(compressed=True,is_ret=True).gen(f.t) + " " + f.name + "() const {")
            out_cls.inc_indent()
            # Return the raw pointer held by a unique pointer. Return everything else by value
            if isinstance(f.t, TypePointer) and f.t.pt == PointerKind.Unique:
                out_cls.println("return m_" + f.name + ".get();")
            else:
                out_cls.println("return m_" + f.name + ";")
            out_cls.dec_indent()
            out_cls.println("}")

            # TODO: Generate an accessor for adding list elements            
            # TODO: Generate an accessor for accessing individual elements            
            
        # Visitor call
        out_cls.println("virtual void accept(IVisitor *v) { v->visit" + c.name + "(this);}")
        
        out_cls.dec_indent()
        out_cls.println();
        out_cls.println("private:\n")
        out_cls.inc_indent()
        for f in c.data:
            out_cls.println(TypeNameGen(True).gen(f.t) + " m_" + f.name + ";")
        out_cls.dec_indent()
        
        
        out_cls.write("};\n")
        
        if self.namespace is not None:
            out_cls.println()
            out_cls.println("} /* namespace " + self.namespace + " */")
            out_cls.println()

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
            if d.circular:
                out_cpp.println("#include \"" + key + ".h\"")
                
        out_cpp.println()
        
        if self.namespace is not None:
            out_cpp.println("namespace " + self.namespace + " {")
            out_cpp.println()
            
        out_cpp.println(c.name + "::" + c.name + "(")
        out_cpp.inc_indent()
        params = list(filter(lambda d : d.is_ctor, c.data))
        for i,p in enumerate(params):
            out_cpp.println(
                TypeNameGen(compressed=True,is_ret=True).gen(p.t) + " " + p.name + 
                    ("," if i+1 < len(params) else ") :"))
        out_cpp.dec_indent()
        if len(params) == 0:
            out_cpp.println(") {")
        else:
            out_cpp.inc_indent()
            out_cpp.inc_indent()
            for i,p in enumerate(params):
                out_cpp.println("m_" + p.name + "(" + p.name + ")" +
                                ("," if i+1 < len(params) else " {"))
            out_cpp.dec_indent()
            out_cpp.dec_indent()

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
        
        if self.namespace is not None:
            out_cpp.println()
            out_cpp.println("} /* namespace " + self.namespace + " */")
        
        return out_cpp.content()
    
    def gen_cmake(self, ast):
        out = OutStream()
        project = "project"
        out.println("#****************************************************************************")
        out.println("#* CMakeLists.txt for " + project)
        out.println("#****************************************************************************")
        out.println()
        out.println("cmake_minimum_required (VERSION 2.8)")
        out.println()
        out.println("project (" + project + ")")
        out.println()
        out.println("file(GLOB_RECURSE " + project + "_SRC")
        out.inc_indent()
        out.println("\"*.h\"")
        out.println("\"*.cpp\"")
        out.dec_indent()
        out.println(")")
        out.println()
        out.println("add_library(" + project + "_ast ${" + project + "_SRC})")
        out.println()
        out.println("install(TARGETS " + project + "_ast")
        out.inc_indent()
        out.println("DESTINATION lib")
        out.println("EXPORT " + project + "_ast-targets)")
        out.dec_indent()
        out.println()
        out.println("install(DIRECTORY \"${PROJECT_SOURCE_DIR}/\"")
        out.inc_indent()
        out.println("DESTINATION \"include/" + project + "_ast\"")
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
            self.out.write(TypeNameGen().gen(t))
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

class TypeNameGen(Visitor):
    
    def __init__(self, compressed=False, is_ret=False):
        self.out = ""
        self.compressed = compressed
        self.is_ret = is_ret
        self.depth = 0
        
    def gen(self, t):
        t.accept(self)
        return self.out
    
    def visitTypeList(self, t):
        if self.depth == 0:
            self.depth += 1
            if self.is_ret:
                self.out += "const "
            
            self.out += "std::vector<"
            self.out += TypeNameGen(compressed=self.compressed).gen(t.t)
            self.out += ">"
        
            if self.is_ret:
                self.out += "&"
            self.depth -= 1
        else:
            self.out += TypeNameGen().gen(t)
            
        
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
            self.out += TypeNameGen().gen(t)

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
        self.out += vmap[t.t]
    
    def visitTypeUserDef(self, t):
        self.out += t.name
        
class GetPointerType(Visitor):
    def __init__(self):
        self.out = ""
        
    def gen(self, t):
        t.accept(self)
        return self.out
    
    def visitTypeUserDef(self, t):
        self.out += t.name
        