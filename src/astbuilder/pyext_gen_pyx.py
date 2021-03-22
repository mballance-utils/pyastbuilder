'''
Created on Mar 22, 2021

@author: mballance
'''
from astbuilder.ast_class import AstClass
from astbuilder.ast_data import AstData
from astbuilder.outstream import OutStream
from astbuilder.pyext_accessor_gen import PyExtAccessorGen
from astbuilder.pyext_type_name_gen import PyExtTypeNameGen
from astbuilder.visitor import Visitor
import os


class PyExtGenPyx(Visitor):
    
    def __init__(self,
                 outdir,
                 name, 
                 namespace):
        self.outdir = outdir
        self.name = name
        self.namespace = namespace
        
    def gen(self, ast):
        self.pyx = OutStream()
        self.pxd = OutStream()
        
        self.gen_defs(self.pxd)
        self.gen_defs(self.pyx)
        
        self.pyx.println("import %s_decl" % self.name)
        
        ast.accept(self)
        
        with open(os.path.join(self.outdir, "%s_decl.pxd" % self.name), "w") as f:
            f.write(self.pxd.content())
            
        with open(os.path.join(self.outdir, "%s.pyx" % self.name), "w") as f:
            f.write(self.pyx.content())
    
    def gen_defs(self, out):
        out.println("from libcpp.string cimport string as      std_string")
        out.println("from libcpp.map cimport map as            std_map")
        out.println("from libcpp.memory cimport unique_ptr as  std_unique_ptr")
        out.println("from libcpp.memory cimport shared_ptr as  std_shared_ptr")
        out.println("from libcpp.vector cimport vector as std_vector")
        out.println("from libcpp.utility cimport pair as  std_pair")
        out.println("from libcpp cimport bool as          bool")

        out.println("ctypedef char                 int8_t")
        out.println("ctypedef unsigned char        uint8_t")
        out.println("ctypedef short                int16_t")
        out.println("ctypedef unsigned short       uint16_t")
        out.println("ctypedef int                  int32_t")
        out.println("ctypedef unsigned int         uint32_t")
        out.println("ctypedef long long            int64_t")
        out.println("ctypedef unsigned long long   uint64_t")    
        
    def visitAstClass(self, c : AstClass):
        if self.namespace is not None:
            self.pxd.println("cdef extern from \"%s.h\" namespace %s:" % (c.name, self.namespace))
        else:
            self.pxd.println("cdef extern from \"%s.h\":" % c.name)
        self.pxd.inc_indent()
        if c.super is not None:
            self.pxd.println("cpdef cppclass %s(%s):" % (c.name, PyExtTypeNameGen().gen(c.super)))
        else:
            self.pxd.println("cpdef cppclass %s:" % c.name)


        self.pxd.inc_indent()
        if len(c.data) > 0:
            super().visitAstClass(c)
        else:
            self.pxd.println("pass")
        self.pxd.dec_indent()
        
        self.pxd.dec_indent()

    def visitAstData(self, d:AstData):
        print("visitAstData")
        PyExtAccessorGen(self.pxd, self.pyx).gen(d)
                