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
from astbuilder.cpp_gen_fwd_decl import CppGenFwdDecl


class GenCppVisitor(Visitor):
    
    def __init__(self, 
                 outdir, 
                 license,
                 namespace):
        self.outdir = outdir
        self.license = license
        self.namespace = namespace
        
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
        
        if self.namespace is not None:
            out.println("namespace " + self.namespace + " {")

        CppGenFwdDecl(out).gen(ast)
        out.println()
        
        out_m.println("class IVisitor {")
        out_m.println("public:")
        out_m.inc_indent()
        out_m.println("virtual ~IVisitor() { }")
        out_m.println()
        
        for c in ast.classes:
            out.println("class " + c.name + ";")
            out_m.println("virtual void visit" + c.name + "(I" + c.name + " *i) = 0;")
            out_m.println()
            
        out_m.dec_indent();
        out_m.println("};")
        
        out.println()
        
        if self.namespace is not None:
            out_m.println("} /* namespace " + self.namespace + " */")
            out_m.println()

        if self.namespace is not None:            
            incdir = os.path.join(self.outdir, "include", self.namespace)
        else:
            incdir = os.path.join(self.outdir, "include")
            
        if not os.path.isdir(incdir):
            os.makedirs(incdir)
        
        with open(os.path.join(incdir, "IVisitor.h"), "w") as fp:
            fp.write(
                out.content() +
                out_m.content()
            )
        
    def gen_base_visitor(self, ast):
        out_h = OutStream()
        out_h_c = OutStream()
        
        out_h.println("/****************************************************************************")
        out_h.println(" * VisitorBase.h")
        if self.license is not None:
            out_h.write(self.license)
        out_h.println(" ****************************************************************************/")
        out_h.println("#pragma once")
        out_h.println("#include \"IVisitor.h\"")
        out_h.println()
        
        if self.namespace is not None:
            out_h_c.println("namespace " + self.namespace + " {")
            out_h_c.println()
        
        out_h_c.println("class VisitorBase : public virtual IVisitor {")
        out_h_c.println("public:")
        out_h_c.inc_indent()
        out_h_c.println("VisitorBase(IVisitor *this_p=0) : m_this(this_p?this_p:this) { }")
        out_h_c.println()
        out_h_c.println("virtual ~VisitorBase() { }")
        out_h_c.println()
        
        for c in ast.classes:
            if self.namespace is not None:
                out_h.println("#include \"%s/I%s.h\"" % (self.namespace, c.name))
            else:
                out_h.println("#include \"I%s.h\"" % c.name)
            out_h_c.println("virtual void visit" + c.name + "(I" + c.name + " *i) override {")
            out_h_c.inc_indent()
            self.gen_class_visitor(out_h_c, c)
            out_h_c.dec_indent()
            out_h_c.println("}")
            out_h_c.println()
            
        out_h_c.println()
        out_h_c.println("protected:")
        out_h_c.inc_indent()
        out_h_c.println("IVisitor *m_this;")
        out_h_c.dec_indent()
        
        out_h.println()
        out_h_c.dec_indent()
        out_h_c.println("};")
        out_h_c.println()
        
        if self.namespace is not None:
            out_h_c.println("} /* namespace " + self.namespace + " */")
            out_h_c.println()
            
        if self.namespace is not None:            
            incdir = os.path.join(self.outdir, "include", self.namespace)
        else:
            incdir = os.path.join(self.outdir, "include")
            
        impldir = os.path.join(incdir, "impl")
            
        if not os.path.isdir(impldir):
            os.makedirs(impldir)

        with open(os.path.join(impldir, "VisitorBase.h"), "w") as fp:
            fp.write(
                out_h.content() +
                out_h_c.content()
            )
            
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
                    out_cpp.println("it=i->get_" + d.name + "().begin();")
                    out_cpp.println("it!=i->get_" + d.name + "().end(); it++) {")
                    out_cpp.dec_indent()
                    out_cpp.println("(*it)->accept(this);")
                    out_cpp.dec_indent()
                    out_cpp.println("}")
            elif isinstance(d.t, TypePointer):
                out_cpp.println("if (i->get_" + d.name + "()) {")
                out_cpp.inc_indent()
                out_cpp.println("i->get_" + d.name + "()->accept(this);")
                out_cpp.dec_indent()
                out_cpp.println("}")
            
