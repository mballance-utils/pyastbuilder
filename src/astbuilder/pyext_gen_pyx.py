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
from astbuilder.type_pointer import TypePointer
from astbuilder.type_userdef import TypeUserDef
from astbuilder.pyext_gen_ptrdefs import PyExtGenPtrDef


class PyExtGenPyx(Visitor):
    
    def __init__(self,
                 outdir,
                 name, 
                 namespace,
                 decl_pxd,
                 pxd,
                 pyx):
        self.outdir = outdir
        self.name = name
        self.namespace = namespace
        self.decl_pxd = decl_pxd
        self.pxd = pxd
        self.pyx = pyx
        
    def gen(self, ast):
        
        self.pyx.println("# cython: language_level=3")
        self.pxd.println("# cython: language_level=3")
        self.decl_pxd.println("# cython: language_level=3")
        
        self.gen_defs(self.decl_pxd)
        PyExtGenPtrDef(self.decl_pxd).gen(ast)
        self.gen_defs(self.pxd)
#        self.gen_defs(self.pyx)
        
        self.pxd.println("cimport %s_decl" % self.name)
        self.pyx.println("cimport %s_decl" % self.name)
        
        for e in ast.enums:
            self.decl_pxd.println("ctypedef enum %s:" % e.name)
            self.decl_pxd.inc_indent()
            for i,v in enumerate(e.values):
                self.decl_pxd.println("%s%s" % (v[0], "," if i+1 < len(e.values) else ""))
            self.decl_pxd.dec_indent()
            self.pyx.println("ctypedef %s_decl.%s %s" % (self.name, e.name, e.name))
        
        ast.accept(self)
        
    
    def gen_defs(self, out):
        out.println("from libcpp.cast cimport dynamic_cast")
        out.println("from libcpp.cast cimport static_cast")
        out.println("from libcpp.string cimport string as      std_string")
        out.println("from libcpp.map cimport map as            std_map")
        out.println("from libcpp.memory cimport unique_ptr as  std_unique_ptr")
        out.println("from libcpp.memory cimport shared_ptr as  std_shared_ptr")
        out.println("from libcpp.vector cimport vector as std_vector")
        out.println("from libcpp.utility cimport pair as  std_pair")
        out.println("from libcpp cimport bool as          bool")
        out.println("cimport cpython.ref as cpy_ref")
        out.println()

        out.println("ctypedef char                 int8_t")
        out.println("ctypedef unsigned char        uint8_t")
        out.println("ctypedef short                int16_t")
        out.println("ctypedef unsigned short       uint16_t")
        out.println("ctypedef int                  int32_t")
        out.println("ctypedef unsigned int         uint32_t")
        out.println("ctypedef long long            int64_t")
        out.println("ctypedef unsigned long long   uint64_t")
        out.println()
        
        
        
    def visitAstClass(self, c : AstClass):
        
        # Generate the prototype that goes in the .decl_pxd
        if self.namespace is not None:
            self.decl_pxd.println("cdef extern from \"%s/I%s.h\" namespace \"%s\":" % (c.name, self.namespace, self.namespace))
        else:
            self.decl_pxd.println("cdef extern from \"I%s.h\":" % c.name)
            
        self.decl_pxd.inc_indent()
        
        if c.super is not None:
            self.decl_pxd.println("cpdef cppclass I%s(I%s):" % (c.name, PyExtTypeNameGen().gen(c.super)))
        else:
            self.decl_pxd.println("cpdef cppclass I%s:" % c.name)
            
        # Generate the ctor
        self.decl_pxd.inc_indent()
        params = self.collect_ctor_params(c)
        if len(params) == 0:
            self.decl_pxd.println("%s()" % c.name)
        else:
            self.decl_pxd.println("%s(" % c.name)
            self.decl_pxd.inc_indent()
            for i,p in enumerate(params):
                if i > 0:
                    self.decl_pxd.write(",\n")
                self.decl_pxd.write(self.decl_pxd.ind)
                self.decl_pxd.write(PyExtTypeNameGen(compressed=True,is_ret=True).gen(p.t) + " ")
                self.decl_pxd.write(p.name)
            self.decl_pxd.dec_indent()
            self.decl_pxd.write(")\n")
        
        # Generate the wrapper that goes in the .pyx
        if c.super is not None:
            self.pyx.println("cdef class %s(%s):" % (c.name, PyExtTypeNameGen(is_pytype=True).gen(c.super)))
            self.pxd.println("cdef class %s(%s):" % (c.name, PyExtTypeNameGen(is_pytype=True).gen(c.super)))
        else:
            self.pyx.println("cdef class %s(object):" % c.name)
            self.pxd.println("cdef class %s(object):" % c.name)
            
                        
        self.pyx.inc_indent()
        self.pxd.inc_indent()
        
        if c.super is None:
            self.pxd.println("cdef %s_decl.I%s    *_hndl" % (self.name, c.name))
            self.pxd.println("cdef bool           _owned")
            
        self.pyx.println()
        self.pxd.println()
            
#        self.pyx.println("def __init__(self):")
#        self.pyx.inc_indent()
#        self.pyx.println("self._owned = False")
#        self.pyx.dec_indent()
        
        if c.super is None:
            self.pyx.println("def __dealloc__(self):")
            self.pyx.inc_indent()
            self.pyx.println("if self._owned and self._hndl != NULL:")
            self.pyx.inc_indent()
            self.pyx.println("del self._hndl")
            self.pyx.dec_indent()
            self.pyx.dec_indent()
            self.pyx.println()
            
            self.pyx.println("cpdef void accept(self, VisitorBase v):")
            self.pyx.inc_indent()
            self.pyx.println("self._hndl.accept(v._hndl)")
            self.pyx.dec_indent()
            self.pyx.println()
            
            self.pxd.println("cpdef void accept(self, VisitorBase v)")
            
        self.pyx.println("@staticmethod")
        self.pyx.println("cdef %s mk(%s_decl.I%s *hndl, bool owned):" % (c.name, self.name, c.name))
        self.pyx.inc_indent()
        self.pyx.println("'''Creates a Python wrapper around native class'''")
        self.pyx.println("ret = %s()" % c.name)
        self.pyx.println("ret._hndl = hndl")
        self.pyx.println("ret._owned = owned")
        self.pyx.println("return ret")
        self.pyx.dec_indent()
        self.pyx.println()
        
        self.pxd.println("@staticmethod")
        self.pxd.println("cdef %s mk(%s_decl.I%s *hndl, bool owned)" % (c.name, self.name, c.name))
        
        # TODO: Handle ctor parameters        
#         self.pyx.println("@staticmethod")
#         if len(c.data) == 0:
#             self.pyx.println("def create():")
#         else:
#             self.pyx.println("def create(")
#             self.pyx.inc_indent()
#             self.gen_ctor_params(c, True, self.pyx)
#             self.pyx.dec_indent()
#             self.pyx.write("):\n")
#         self.pyx.inc_indent()
#         self.pyx.println("'''Creates a Python wrapper around a new native class'''")
#         self.pyx.println("ret = %s()" % c.name)
#         if len(params) == 0:
#             self.pyx.println("ret._hndl = new %s_decl.%s()" % (self.name, c.name))
#         else:
#             self.pyx.write("%sret._hndl = new %s_decl.%s(" % (self.pyx.ind, self.name, c.name))
#             for i,p in enumerate(params):
#                 if i>0:
#                     self.pyx.write(", ")
#                 # TODO: ref '_hndl' if it is a user-defined type
#                 if isinstance(p.t, TypePointer):
#                     self.pyx.write("<%s_decl.%s *>%s._hndl" % (self.name, 
#                         PyExtTypeNameGen(is_pyx=True).gen(p.t), p.name))
#                 else:
#                     self.pyx.write("%s" % p.name)
#             self.pyx.write(")\n")
#                 
#         self.pyx.println("ret._owned = True")
#         self.pyx.println("return ret")
#         self.pyx.dec_indent()
#         self.pyx.println()

        if len(c.data) > 0:
            for d in c.data:
                PyExtAccessorGen(self.name, c.name, self.decl_pxd, self.pxd, self.pyx).gen(d)
        else:
            self.decl_pxd.println("pass")
            
        if c.super is None:
            self.decl_pxd.println("void accept(VisitorBase *v)")
            
        self.decl_pxd.dec_indent()
        self.pyx.dec_indent()
        self.pxd.dec_indent()
        
        self.decl_pxd.dec_indent()        
        self.pyx.dec_indent()        
        self.pxd.dec_indent()
        
        self.decl_pxd.println()
        self.pyx.println()
        self.pxd.println()

    def visitAstData(self, d:AstData):
        print("visitAstData")
        
    def gen_ctor_params(self, 
                        c, 
                        is_pyx,
                        out):
        """Returns True if this level (or a previous level) added content"""
        ret = False
        if c.super is not None:
            # Recurse first
            ret |= self.gen_ctor_params(c.super.target, is_pyx, out)
            
        params = list(filter(lambda d : d.is_ctor, c.data))
        for i,p in enumerate(params):
            if ret and i == 0:
                out.write(",\n")
            out.write(out.ind)
            out.write(PyExtTypeNameGen(compressed=True,is_pyx=is_pyx, is_ret=True).gen(p.t) + " ")
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
