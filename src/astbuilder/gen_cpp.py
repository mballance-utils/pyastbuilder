'''
Created on Sep 12, 2020

@author: ballance
'''
import os
import shutil

from astgen.ast import Ast
from astgen.ast_class import AstClass
from astgen.outstream import OutStream
from astgen.type_pointer import TypePointer, PointerKind
from astgen.type_userdef import TypeUserDef
from astgen.visitor import Visitor
from astgen.gen_cpp_visitor import GenCppVisitor
from astgen.type_list import TypeList


class GenCPP(Visitor):
    
    def __init__(self, outdir):
        self.outdir = outdir
        pass
    
    def generate(self, ast):
        ast.accept(self)
        GenCppVisitor(self.outdir).generate(ast)
        
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
            
            
        
    def define_class_h(self, c):
        out_inc = OutStream()
        out_cls = OutStream()
        
        out_h = OutStream()
        out_h.println("/****************************************************************************")
        out_h.println(" * " + c.name + ".h")
        out_h.println(" ****************************************************************************/")
        out_h.println("#pragma once")
        out_h.println("#include <map>")
        out_h.println("#include <memory>")
        out_h.println("#include <set>")
        out_h.println("#include <string>")
        out_h.println("#include <vector>")
        out_h.println("#include \"IVisitor.h\"")
        
        if c.super is not None:
            out_h.println("#include \"" + c.super + ".h\"")
            out_h.println()

        # Create forward references
        out_h.println(FieldForwardRefGen().gen(c))
        
        out_cls.write("class " + c.name)
        
        if c.super is not None:
            out_cls.write(" : public " + c.super)
        out_cls.write(" {\n")
        out_cls.write("public:\n")
        out_cls.inc_indent()
        out_cls.println(c.name + "(");
        out_cls.inc_indent()
        # TODO: constructor arguments
        out_cls.println(");");
        out_cls.dec_indent()
        
        out_cls.println();
        out_cls.println("virtual ~" + c.name + "() { }");
        
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

        return (out_h.content() + 
                out_inc.content() +
                out_cls.content())
    
    def define_class_cpp(self, c):
        out_cpp = OutStream()
        out_cpp.println("/****************************************************************************")
        out_cpp.println(" * " + c.name + ".cpp")
        out_cpp.println(" ****************************************************************************/")
        out_cpp.println("#include \"" + c.name + ".h\"")
        out_cpp.println()
        out_cpp.println(FieldIncludeGen().gen(c))
        
        # TODO: include dependencies
        
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
        
        return out.content()
        
    
class FieldForwardRefGen(Visitor):
       
    def __init__(self):
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
        