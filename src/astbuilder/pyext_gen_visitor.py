'''
Created on Mar 23, 2021

@author: mballance
'''
from astbuilder.visitor import Visitor

class PyExtGenVisitor(Visitor):
    
    def __init__(self,
                 name,
                 namespace,
                 pxd,
                 pyx,
                 cpp,
                 hpp):
        self.name = name
        self.namespace = namespace
        self.pxd = pxd
        self.pyx = pyx
        self.cpp = cpp
        self.hpp = hpp

    def gen(self, ast):
        # Generate a C++ class with 
        # - Holds a handle to a cdef proxy class
        # - py_prefixed visitor methods to be called from Python
        # - un-prefixed visitor methods to be called from C++
        #
        # Generate an import class that mirrors the base visitor
        # Generate an import class in pxd that mirrors this class
        #
        # Generate a cdef class in pyx with just 
        
        self.gen_visitor_imp(ast)
        self.gen_visitor(ast)
        self.gen_py_base_visitor(ast)
        
        pass
    
    def gen_visitor_imp(self, ast):
        """Generate the pxd view of the base visitor"""

        # Define the AST BaseVisitor class
        if self.namespace is not None:
            self.pxd.println("cdef extern from '%s.h' namespace %s:" % ("BaseVisitor", self.namespace))
        else:
            self.pxd.println("cdef extern from '%s.h':" % "BaseVisitor")
            
        self.pxd.inc_indent()
        self.pxd.println("cpdef cppclass %s:" % "BaseVisitor")
        self.pxd.inc_indent()
        for c in ast.classes:
            self.pxd.println("void visit%s(%s *i)" % (c.name, c.name))
        self.pxd.dec_indent()
        self.pxd.dec_indent()
        
        if self.namespace is not None:
            self.pxd.println("cdef extern from '%s.h' namespace %s:" % ("PyBaseVisitor", self.namespace))
        else:
            self.pxd.println("cdef extern from '%s.h':" % "PyBaseVisitor")
            
        self.pxd.inc_indent()
        self.pxd.println("cpdef cppclass %s(%s):" % ("PyBaseVisitor", "BaseVisitor"))
        self.pxd.inc_indent()
        self.pxd.println("PyBaseVisitor(cpy_ref.PyObject *)")
        for c in ast.classes:
            self.pxd.println("void py_visit%s(%s *i)" % (c.name, c.name))
        self.pxd.dec_indent()
        self.pxd.dec_indent()
        
    def gen_visitor(self, ast):
        """Generates cdef class that user can extend"""
        
        self.pyx.println("cdef class BaseVisitor(object):")
        self.pyx.inc_indent()
        self.pyx.println("cdef %s_decl.PyBaseVisitor *thisptr" % self.name)
        self.pyx.println("def __cinit__(self):")
        self.pyx.inc_indent()
        self.pyx.println("self.thisptr = new %s_decl.PyBaseVisitor(<cpy_ref.PyObject*>self)" %
                         (self.name,))
        self.pyx.dec_indent()
        
        for c in ast.classes:
            self.pyx.println("cpdef void visit%s(self, %s i):" % (c.name, c.name))
            self.pyx.inc_indent()
            self.pyx.println("self.thisptr.py_visit%s(<%s_decl.%s *>i.thisptr);" % 
                             (c.name, self.name, c.name))
            self.pyx.dec_indent()
        self.pyx.dec_indent()
        
    def gen_py_base_visitor(self, ast):
        self.hpp.println("#pragma once")
        self.hpp.println("#include \"BaseVisitor.h\"")
        self.hpp.println("#include \"%s_api.h\"" % self.name)
        
        self.cpp.println("#include \"PyBaseVisitor.h\"")
       
        # Constructor 
        self.hpp.println("class PyBaseVisitor : public BaseVisitor {")
        self.hpp.println("public:")
        self.hpp.inc_indent()
        self.hpp.println("PyBaseVisitor(PyObject *proxy);")
        
        self.cpp.println("PyBaseVisitor::PyBaseVisitor(PyObject *proxy) : m_proxy(proxy) {")
        self.cpp.inc_indent()
        self.cpp.println("import_%s();" % self.name)
        self.cpp.println("Py_XINCREF(m_proxy);")
        self.cpp.dec_indent()
        self.cpp.println("}")
        
        # Destructor 
        self.hpp.println("virtual ~PyBaseVisitor();")
        self.hpp.dec_indent()
        
        self.cpp.println("PyBaseVisitor::~PyBaseVisitor() {")
        self.cpp.inc_indent()
        self.cpp.println("Py_XDECREF(m_proxy);")
        self.cpp.dec_indent()
        self.cpp.println("}")
        
        self.hpp.println("private:")
        self.hpp.inc_indent()
        self.hpp.println("PyObject *m_proxy;")
        
        self.pxd.inc_indent()
        self.hpp.println("public:")
        self.pxd.inc_indent()
        for c in ast.classes:

            # C++-callable visitor method            
            self.hpp.println("virtual void visit%s(%s *i) override;" % (c.name, c.name))
            self.cpp.println("void PyBaseVisitor::visit%s(%s *i) {" % (c.name, c.name))
            self.cpp.inc_indent()
            self.cpp.println("%s_call_visit%s(m_proxy, i);" % (self.name, c.name))
            self.cpp.dec_indent()
            self.cpp.println("}")

            # Python-callable visitor method            
            self.hpp.println("void py_visit%s(%s *i);" % (c.name, c.name))
            self.cpp.println("void PyBaseVisitor::py_visit%s(%s *i) {" % (c.name, c.name))
            self.cpp.inc_indent()
            self.cpp.println("BaseVisitor::visit%s(i);" % c.name)
            self.cpp.dec_indent()
            self.cpp.println("}")
            
            self.pyx.println("cdef public api %s_call_visit%s(object self, %s_decl.%s *i):" % 
                             (self.name, c.name, self.name, c.name))
            self.pyx.inc_indent()
            self.pyx.println("self.visit%s(%s.wrap(i))" % (c.name, c.name))
            self.pyx.dec_indent()
            
        self.pxd.dec_indent()
        self.pxd.dec_indent()

        self.hpp.dec_indent()
        self.hpp.println("};")
        

