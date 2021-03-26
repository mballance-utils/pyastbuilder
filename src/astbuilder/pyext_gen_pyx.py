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
                 namespace,
                 pxd,
                 pyx):
        self.outdir = outdir
        self.name = name
        self.namespace = namespace
        self.pxd = pxd
        self.pyx = pyx
        
    def gen(self, ast):
        
        self.pyx.println("# cython: language_level=3")
        
        self.gen_defs(self.pxd)
        self.gen_defs(self.pyx)
        
        self.pyx.println("cimport %s_decl" % self.name)
        
        ast.accept(self)
        
    
    def gen_defs(self, out):
        out.println("from libcpp.string cimport string as      std_string")
        out.println("from libcpp.map cimport map as            std_map")
        out.println("from libcpp.memory cimport unique_ptr as  std_unique_ptr")
        out.println("from libcpp.memory cimport shared_ptr as  std_shared_ptr")
        out.println("from libcpp.vector cimport vector as std_vector")
        out.println("from libcpp.utility cimport pair as  std_pair")
        out.println("from libcpp cimport bool as          bool")
        out.println("cimport cpython.ref as cpy_ref")


        out.println("ctypedef char                 int8_t")
        out.println("ctypedef unsigned char        uint8_t")
        out.println("ctypedef short                int16_t")
        out.println("ctypedef unsigned short       uint16_t")
        out.println("ctypedef int                  int32_t")
        out.println("ctypedef unsigned int         uint32_t")
        out.println("ctypedef long long            int64_t")
        out.println("ctypedef unsigned long long   uint64_t")    
        
    def visitAstClass(self, c : AstClass):
        
        # Generate the prototype that goes in the .pxd
        if self.namespace is not None:
            self.pxd.println("cdef extern from \"%s.h\" namespace \"%s\":" % (c.name, self.namespace))
        else:
            self.pxd.println("cdef extern from \"%s.h\":" % c.name)
        self.pxd.inc_indent()
        if c.super is not None:
            self.pxd.println("cpdef cppclass %s(%s):" % (c.name, PyExtTypeNameGen().gen(c.super)))
        else:
            self.pxd.println("cpdef cppclass %s:" % c.name)
            
        # Generate the ctor
        self.pxd.inc_indent()
        params = self.collect_ctor_params(c)
        if len(params) == 0:
            self.pxd.println("%s()" % c.name)
        else:
            self.pxd.println("%s(" % c.name)
            self.pxd.inc_indent()
            for i,p in enumerate(params):
                if i > 0:
                    self.pxd.write(",\n")
                self.pxd.write(self.pxd.ind)
                self.pxd.write(PyExtTypeNameGen(compressed=True,is_ret=True).gen(p.t) + " ")
                self.pxd.write(p.name)
            self.pxd.dec_indent()
            self.pxd.write(")\n")
        
        # Generate the wrapper that goes in the .pyx
        if c.super is not None:
            self.pyx.println("cdef class %s(%s):" % (c.name, PyExtTypeNameGen().gen(c.super)))
        else:
            self.pyx.println("cdef class %s(object):" % c.name)
            
                        
        self.pyx.inc_indent()
        
        if c.super is None:
            self.pyx.println("cdef %s_decl.%s     *thisptr" % (self.name, c.name))
            self.pyx.println("cdef bool           owned")
            
        self.pyx.println()
            
        self.pyx.println("def __cinit__(self):")
        self.pyx.inc_indent()
        if c.super is None:
            self.pyx.println("pass")
        else:
            self.pyx.println("self.owned = False")
        self.pyx.dec_indent()
        self.pyx.println()
        
        if c.super is None:
            self.pyx.println("def __dealloc__(self):")
            self.pyx.inc_indent()
            self.pyx.println("if self.owned:")
            self.pyx.inc_indent()
            self.pyx.println("del self.thisptr")
            self.pyx.dec_indent()
            self.pyx.dec_indent()
            self.pyx.println()
            
            self.pyx.println("cpdef void accept(self, BaseVisitor v):")
            self.pyx.inc_indent()
            self.pyx.println("self.thisptr.accept(v.thisptr)")
            self.pyx.dec_indent()
            
        self.pyx.println("@staticmethod")
        self.pyx.println("cdef %s wrap(%s_decl.%s *thisptr):" % (c.name, self.name, c.name))
        self.pyx.inc_indent()
        self.pyx.println("'''Creates a Python wrapper around native class'''")
        self.pyx.println("ret = %s()" % c.name)
        self.pyx.println("ret.thisptr = thisptr")
        self.pyx.println("return ret")
        self.pyx.dec_indent()
        self.pyx.println()

        # TODO: Handle ctor parameters        
        self.pyx.println("@staticmethod")
        if len(c.data) == 0:
            self.pyx.println("def create():")
        else:
            self.pyx.println("def create(")
            self.pyx.inc_indent()
            self.gen_ctor_params(c, self.pyx)
            self.pyx.dec_indent()
            self.pyx.write("):\n")
        self.pyx.inc_indent()
        self.pyx.println("'''Creates a Python wrapper around native class'''")
        self.pyx.println("ret = %s()" % c.name)
        if len(params) == 0:
            self.pyx.println("ret.thisptr = new %s_decl.%s()" % (self.name, c.name))
        else:
            self.pyx.write("%sret.thisptr = new %s_decl.%s(" % (self.pyx.ind, self.name, c.name))
            for i,p in enumerate(params):
                if i>0:
                    self.pyx.write(", ")
                self.pyx.write("%s" % p.name)
            self.pyx.write(")\n")
                
        self.pyx.println("ret.owned = True")
        self.pyx.println("return ret")
        self.pyx.dec_indent()
        self.pyx.println()

        if len(c.data) > 0:
            for d in c.data:
                PyExtAccessorGen(self.name, c.name, self.pxd, self.pyx).gen(d)
        else:
            self.pxd.println("pass")
            
        if c.super is None:
            self.pxd.println("void accept(BaseVisitor *v)")
            
        self.pxd.dec_indent()
        self.pyx.dec_indent()
        
        self.pxd.dec_indent()        
        self.pyx.dec_indent()        

    def visitAstData(self, d:AstData):
        print("visitAstData")
        
    def gen_ctor_params(self, c, out):
        """Returns True if this level (or a previous level) added content"""
        ret = False
        if c.super is not None:
            # Recurse first
            ret |= self.gen_ctor_params(c.super.target, out)
            
        params = list(filter(lambda d : d.is_ctor, c.data))
        for i,p in enumerate(params):
            if ret and i == 0:
                out.write(",\n")
            out.write(out.ind)
            out.write(PyExtTypeNameGen(compressed=True,is_ret=True).gen(p.t) + " ")
            out.write(p.name + (",\n" if i+1 < len(params) else ""))
            ret = True
        
        return ret        
    
    def collect_ctor_params(self, c):
        if c.super is not None:
            params = self.collect_ctor_params(c.super.target)
        else:
            params = []
            
        params.extend(list(filter(lambda d : d.is_ctor, c.data)))
        
        return params
