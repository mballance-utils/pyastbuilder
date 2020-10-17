'''
Created on Sep 13, 2020

@author: ballance
'''
import os

from astbuilder.outstream import OutStream
from astbuilder.type_list import TypeList
from astbuilder.type_pointer import TypePointer
from astbuilder.visitor import Visitor
from .cpp_type_name_gen import CppTypeNameGen
from astbuilder.type_scalar import TypeScalar


class GenCppVisitor(Visitor):
    
    def __init__(self, outdir, license):
        self.outdir = outdir
        self.license = license
        
    def generate(self, ast):
        self.gen_ifc(ast)
        self.gen_base_visitor(ast)
        
    def gen_ifc(self, ast):
        out = OutStream()
        out_m = OutStream()
        
        out.println("/****************************************************************************")
        out.println(" * IVisitor.h")
        if self.license is not None:
            out.write(self.license)
        out.println(" ****************************************************************************/")
        out.println("#pragma once")
        out.println()
        
        out_m.println("class IVisitor {")
        out_m.println("public:")
        out_m.inc_indent()
        out_m.println("virtual ~IVisitor() { }")
        out_m.println()
        
        for c in ast.classes:
            out.println("class " + c.name + ";")
            out_m.println("virtual void visit" + c.name + "(" + c.name + " *i) = 0;")
            out_m.println()
            
        out_m.dec_indent();
        out_m.println("};")
        
        out.println()
        
        with open(os.path.join(self.outdir, "IVisitor.h"), "w") as fp:
            fp.write(
                out.content() +
                out_m.content()
            )
        
    def gen_base_visitor(self, ast):
        out_h = OutStream()
        out_h_c = OutStream()
        out_cpp = OutStream()
        
        out_h.println("/****************************************************************************")
        out_h.println(" * BaseVisitor.h")
        if self.license is not None:
            out_h.write(self.license)
        out_h.println(" ****************************************************************************/")
        out_h.println("#pragma once")
        out_h.println("#include \"IVisitor.h\"")
        out_h.println()
        
        out_h_c.println("class BaseVisitor : public virtual IVisitor {")
        out_h_c.println("public:")
        out_h_c.inc_indent()
        out_h_c.println("BaseVisitor();")
        out_h_c.println()
        out_h_c.println("virtual ~BaseVisitor();")
        out_h_c.println()
        
        out_cpp.println("/****************************************************************************")
        out_cpp.println(" * BaseVisitor.cpp")
        if self.license is not None:
            out_cpp.write(self.license)
        out_cpp.println(" ****************************************************************************/")
        out_cpp.println("#include \"BaseVisitor.h\"")
        out_cpp.println()
        out_cpp.println("BaseVisitor::BaseVisitor() {")
        out_cpp.println()
        out_cpp.println("}")
        out_cpp.println()
        out_cpp.println("BaseVisitor::~BaseVisitor() {")
        out_cpp.println()
        out_cpp.println("}")
        out_cpp.println()
        
        
        for c in ast.classes:
            out_h.println("#include \"" + c.name + ".h\"")
            out_h_c.println("virtual void visit" + c.name + "(" + c.name + " *i) override;")
            out_h_c.println()
            
            out_cpp.println("void BaseVisitor::visit" + c.name + "(" + c.name + " *i) {")
            out_cpp.inc_indent()
            self.gen_class_visitor(out_cpp, c)
            out_cpp.dec_indent()
            out_cpp.println("}")
            out_cpp.println()
            
            
        out_h.println()
        out_h_c.dec_indent()
        out_h_c.println("};")
        
        with open(os.path.join(self.outdir, "BaseVisitor.h"), "w") as fp:
            fp.write(
                out_h.content() +
                out_h_c.content()
            )
            
        with open(os.path.join(self.outdir, "BaseVisitor.cpp"), "w") as fp:
            fp.write(out_cpp.content())
            
    def gen_class_visitor(self, out_cpp, c):
        if c.super is not None:
            out_cpp.println("visit" + c.super.target.name + "(i);")
        for d in c.data:
            if isinstance(d.t, TypeList):
                # Generate an iterator, as long as the
                # list is of a complex type
                if not isinstance(d.t.t, (TypeScalar,)):
                    out_cpp.println("for (std::vector<" + CppTypeNameGen().gen(d.t.t) + ">::const_iterator")
                    out_cpp.inc_indent()
                    out_cpp.inc_indent()
                    out_cpp.println("it=i->" + d.name + "().begin();")
                    out_cpp.println("it!=i->" + d.name + "().end(); it++) {")
                    out_cpp.dec_indent()
                    out_cpp.println("(*it)->accept(this);")
                    out_cpp.dec_indent()
                    out_cpp.println("}")
            elif isinstance(d.t, TypePointer):
                out_cpp.println("if (i->" + d.name + "()) {")
                out_cpp.inc_indent()
                out_cpp.println("i->" + d.name + "()->accept(this);")
                out_cpp.dec_indent()
                out_cpp.println("}")
            
