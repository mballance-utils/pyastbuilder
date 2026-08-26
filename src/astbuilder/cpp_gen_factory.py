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
                 name,
                 license,
                 namespace):
        self.outdir = outdir
        self.name = name
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

        self.gen_inst(out_h, out_cpp)

        out_ih.println("};")
        out_h.println("};")

        self.gen_inst_accessor(out_h, out_cpp)

        CppGenNS.leave(self.namespace, out_ih)
        CppGenNS.leave(self.namespace, out_h)
        CppGenNS.leave(self.namespace, out_cpp)

        self.gen_factory_ext(out_cpp)

        incdir = CppGenNS.incdir(self.outdir, self.namespace)

        with open(os.path.join(incdir, "FactoryExt.h"), "w") as fp:
            fp.write(self.gen_factory_ext_h())
        with open(os.path.join(incdir, "IFactory.h"), "w") as fp:
            fp.write(out_ih.content())
        with open(os.path.join(self.outdir, "Factory.h"), "w") as fp:
            fp.write(out_h.content())
        with open(os.path.join(self.outdir, "Factory.cpp"), "w") as fp:
            fp.write(out_cpp.content())
        
        pass
    
    def gen_ih_prelude(self, out):
        out.println("#include <memory>")
        for e in self.ast.enums:
            out.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "%s.h"%e.name))
        for c in self.ast.classes:
            out.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "I%s.h"%c.name))
            
        CppGenNS.enter(self.namespace, out)
        
        out.println("class IFactory;")
        out.println("using IFactoryUP=std::unique_ptr<IFactory>;")
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
        out.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "FactoryExt.h"))
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

    def gen_inst(self, out_h, out_cpp):
        out_h.println()
        out_h.inc_indent()
        out_h.println("static IFactory *inst();")
        out_h.println()
        out_h.dec_indent()
        out_h.println("private:")
        out_h.inc_indent()
        out_h.println("static std::unique_ptr<Factory>      m_inst;")
        out_h.dec_indent()

        out_cpp.println()
        out_cpp.println("IFactory *Factory::inst() {")
        out_cpp.inc_indent()
        out_cpp.println("if (!m_inst) {")
        out_cpp.inc_indent()
        out_cpp.println("m_inst = std::unique_ptr<Factory>(new Factory());")
        out_cpp.dec_indent()
        out_cpp.println("}")
        out_cpp.println("return m_inst.get();")
        out_cpp.dec_indent()
        out_cpp.println("}")
        pass

    @property
    def api_macro(self):
        """Name of the macro carrying the entry point's visibility attribute."""
        return "%s_FACTORY_API" % self.name.upper()

    @property
    def build_dll_macro(self):
        """Defined by the library's own build to select the dllexport side."""
        return "%s_BUILD_DLL" % self.name.upper()

    def qualified(self, sym):
        if self.namespace is None or self.namespace == "":
            return sym
        else:
            return "%s::%s" % (self.namespace, sym)

    def gen_inst_accessor(self, out_h, out_cpp):
        out_cpp.println("std::unique_ptr<Factory> Factory::m_inst;")

    def gen_factory_ext(self, out_cpp):
        """Emit the exported entry point.

        Deliberately at global scope, outside the namespace block: the
        definition has to pick up the visibility attribute that FactoryExt.h
        puts on the declaration.
        """
        out_cpp.println("extern \"C\" %s %s *%s_getFactory() {" % (
            self.api_macro,
            self.qualified("IFactory"),
            self.name))
        out_cpp.inc_indent()
        out_cpp.println("return %s::inst();" % self.qualified("Factory"))
        out_cpp.dec_indent()
        out_cpp.println("}")

    def gen_factory_ext_h(self):
        """Header declaring the library's sole exported symbol.

        Everything else in the API is reached through the pure-virtual
        interfaces the factory returns, so this one entry point is the entire
        exported surface.  Windows needs that visibility declared explicitly:
        without it the symbol is absent from the export table, so neither
        GetProcAddress nor a link against the import library can find it --
        and exporting everything instead costs megabytes of mangled names in
        both the DLL and its import library.
        """
        out = OutStream()
        out.println("/****************************************************************************")
        out.println(" * FactoryExt.h")
        if self.license is not None:
            out.write(self.license)
        out.println(" ****************************************************************************/")
        out.println("#pragma once")
        out.println("#include \"%s\"" % CppGenNS.incpath(self.namespace, "IFactory.h"))
        out.println()
        out.println("#if defined(_WIN32)")
        out.println("#  if defined(%s)" % self.build_dll_macro)
        out.println("#    define %s __declspec(dllexport)" % self.api_macro)
        out.println("#  else")
        out.println("#    define %s __declspec(dllimport)" % self.api_macro)
        out.println("#  endif")
        out.println("#else")
        out.println("#  define %s" % self.api_macro)
        out.println("#endif")
        out.println()
        out.println("extern \"C\" %s %s *%s_getFactory();" % (
            self.api_macro,
            self.qualified("IFactory"),
            self.name))

        return out.content()


    