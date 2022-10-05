'''
Created on May 28, 2022

@author: mballance
'''
import os

from astbuilder.cpp_gen_ns import CppGenNS
from astbuilder.outstream import OutStream
from astbuilder.cpp_gen_params import CppGenParams


class CppGenFactory(object):
    
    def __init__(self, 
                 outdir,
                 license,
                 namespace):
        self.outdir = outdir
        self.license = license
        self.namespace = namespace
        pass
    
    def gen(self, ast):
        self.ast = ast
        out_h = OutStream()
        out_ih = OutStream()
        out_cpp = OutStream()

        for name,h in (("Factory.h", out_h), ("IFactory.h", out_ih)):
            h.println("/****************************************************************************")
            h.println(" * %s" % name)
            if self.license is not None:
                h.write(self.license)
            h.println(" ****************************************************************************/")
            h.println("#pragma once")
            h.println()

        out_cpp.println("/****************************************************************************")
        out_cpp.println(" * Factory.cpp")
        if self.license is not None:
            out_cpp.write(self.license)
        out_cpp.println(" ****************************************************************************/")
        out_cpp.println()

        self.gen_ih_prelude(out_ih)
        self.gen_h_prelude(out_h)
        self.gen_cpp_prelude(out_cpp)
        
        # TODO: Add a delegator at some point
        
        self.gen_methods(out_ih, out_h, out_cpp)
        
        out_ih.dec_indent()
        out_h.dec_indent()
        out_ih.println("};")
        out_h.println("};")
        
        CppGenNS.leave(self.namespace, out_ih)
        CppGenNS.leave(self.namespace, out_h)
        CppGenNS.leave(self.namespace, out_cpp)

        incdir = CppGenNS.incdir(self.outdir, self.namespace)
        
        with open(os.path.join(incdir, "IFactory.h"), "w") as fp:
            fp.write(out_ih.content())
        with open(os.path.join(self.outdir, "Factory.h"), "w") as fp:
            fp.write(out_h.content())
        with open(os.path.join(self.outdir, "Factory.cpp"), "w") as fp:
            fp.write(out_cpp.content())
        
        pass
    
    def gen_ih_prelude(self, out):
        for e in self.ast.enums:
            out.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "%s.h"%e.name))
        for c in self.ast.classes:
            out.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "I%s.h"%c.name))
            
        CppGenNS.enter(self.namespace, out)
        
        out.println("class IFactory {")
        out.println("public:")
        out.println()
        out.inc_indent()
        out.println("virtual ~IFactory() { }")
        out.println()
        
    def gen_h_prelude(self, out):
        out.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "IFactory.h"))
        CppGenNS.enter(self.namespace, out)
        
        out.println("class Factory : public virtual IFactory {")
        out.println("public:")
        out.println()
        out.inc_indent()
        out.println("virtual ~Factory();")
        out.println()
        
    def gen_cpp_prelude(self, out):
        out.println("#include \"Factory.h\"")
        for c in self.ast.classes:
            out.println("#include \"%s.h\"" % c.name)
        out.println()
        CppGenNS.enter(self.namespace, out)
        
        out.println("Factory::~Factory() { }")
        out.println()
        
    def gen_methods(self, out_ih, out_h, out_cpp):
        
        for c in self.ast.classes:
            name = c.name[0].upper()+ c.name[1:]
            out_ih.write("%svirtual I%s *mk%s(" % (out_ih.ind, c.name, name))
            CppGenParams.gen_ctor_params(c, out_ih)
            out_ih.write(") = 0;\n")

            out_h.write("%svirtual I%s *mk%s(" % (out_h.ind, c.name, name))
            CppGenParams.gen_ctor_params(c, out_h)
            out_h.write(") override;\n")
            
            out_cpp.println("I%s *Factory::mk%s(" % (c.name, name))
            have_params = CppGenParams.gen_ctor_params(c, out_cpp)
            out_cpp.write(") {\n")
            out_cpp.inc_indent()
            out_cpp.write("%sreturn new %s(" % (out_cpp.ind, c.name))
            CppGenParams.gen_ctor_pvals(c, out_cpp)
            out_cpp.write(");\n")
            out_cpp.dec_indent()
            out_cpp.println("}")
        pass


    