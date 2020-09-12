'''
Created on Sep 12, 2020

@author: ballance
'''
from astgen.ast import Ast
from astgen.visitor import Visitor
from astgen.ast_class import AstClass
from astgen.outstream import OutStream

class GenCPP(Visitor):
    
    def __init__(self, outdir):
        self.outdir = outdir
        pass
    
    def generate(self, ast):
        ast.accept(self)
        
        pass
    
    def visitAstClass(self, c : AstClass):
        h = self.define_class_h(c)
        cpp = self.define_class_cpp(c)
        
        print("Header: " + h)
        print("CPP: " + cpp)
        
        
    def define_class_h(self, c):
        out_inc = OutStream()
        
        out_h = OutStream()
        out_h.println("/****************************************************************************")
        out_h.println(" * " + c.name + ".h")
        out_h.println(" ****************************************************************************/")
        out_h.println("#pragma once")
        
        out_cls = OutStream()
        out_cls.write("class " + c.name)
        out_h.println("")
        
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
        out_cls.dec_indent()
        
        out_cls.println("private:\n")
        out_cls.inc_indent()
        out_cls.dec_indent()
        
        
        out_cls.write("};\n")

        return (out_h.content() + 
                out_inc.content() +
                out_cls.content())
    
    def define_class_cpp(self, c):
        out_cpp = OutStream()
        
        return out_cpp.content()
    
    