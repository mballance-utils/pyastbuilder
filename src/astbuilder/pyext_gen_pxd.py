'''
Created on Mar 21, 2021

@author: mballance
'''
from astbuilder.ast_class import AstClass
from astbuilder.ast_data import AstData
from astbuilder.outstream import OutStream
from astbuilder.pyext_accessor_gen import PyExtAccessorGen
from astbuilder.visitor import Visitor
from astbuilder.pyext_type_name_gen import PyExtTypeNameGen


class PyExtGenPxd(Visitor):
    
    def __init__(self, 
                 out : OutStream,
                 namespace):
        self.out = out
        self.namespace = namespace
        pass
    
    def gen(self, ast):
        self.gen_defs()
        ast.accept(self)
        
    def gen_defs(self):
        self.out.println("from libcpp.string cimport string as      std_string")
        self.out.println("from libcpp.map cimport map as            std_map")
        self.out.println("from libcpp.memory cimport unique_ptr as  std_unique_ptr")
        self.out.println("from libcpp.memory cimport shared_ptr as  std_shared_ptr")
        self.out.println("from libcpp.vector cimport vector as std_vector")
        self.out.println("from libcpp.utility cimport pair as  std_pair")
        self.out.println("from libcpp cimport bool as          bool")

        self.out.println("ctypedef char                 int8_t")
        self.out.println("ctypedef unsigned char        uint8_t")
        self.out.println("ctypedef short                int16_t")
        self.out.println("ctypedef unsigned short       uint16_t")
        self.out.println("ctypedef int                  int32_t")
        self.out.println("ctypedef unsigned int         uint32_t")
        self.out.println("ctypedef long long            int64_t")
        self.out.println("ctypedef unsigned long long   uint64_t")
        
    
    def visitAstClass(self, c : AstClass):
        if self.namespace is not None:
            self.out.println("cdef extern from \"%s.h\" namespace %s:" % (c.name, self.namespace))
        else:
            self.out.println("cdef extern from \"%s.h\":" % c.name)
        self.out.inc_indent()
        if c.super is not None:
            supertype = PyExtTypeNameGen().gen(c.super)
        else:
            supertype = ""
            
        self.out.println("cpdef cppclass %s(%s):" % (c.name, supertype))

        self.out.inc_indent()
        if len(c.data) > 0:
            super().visitAstClass(c)
        else:
            self.out.println("pass")
        self.out.dec_indent()
        
        self.out.dec_indent()

    def visitAstData(self, d:AstData):
        print("visitAstData")
        PyExtAccessorGen(self.out).gen(d)
        