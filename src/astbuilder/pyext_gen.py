'''
Created on Mar 21, 2021

@author: mballance
'''
from astbuilder.ast_class import AstClass
from astbuilder.ast_data import AstData
from astbuilder.gen_cpp import GenCPP
from astbuilder.outstream import OutStream
from astbuilder.visitor import Visitor
from astbuilder.type_pointer import TypePointer
from astbuilder.pyext_accessor_gen import PyExtAccessorGen
import os
from astbuilder.pyext_gen_pxd import PyExtGenPxd
from astbuilder.pyext_gen_extdef import PyExtGenExtDef
from astbuilder.pyext_gen_pyx import PyExtGenPyx
from astbuilder.pyext_gen_visitor import PyExtGenVisitor


class PyExtGen(Visitor):
    
    def __init__(self,
                 outdir,
                 name,
                 target_pkg,
                 license,
                 namespace):
        self.outdir = outdir
        self.name = name
        self.target_pkg = target_pkg
        self.license = license
        self.namespace = namespace

    def generate(self, ast):
        decl_pxd = OutStream()
        pxd = OutStream()
        pyx = OutStream()
        cpp = OutStream()
        hpp = OutStream()
        
        PyExtGenPyx(
            self.outdir, 
            self.name, 
            self.namespace,
            self.target_pkg,
            decl_pxd,
            pxd,
            pyx).gen(ast)
            
        PyExtGenVisitor(
            self.name,
            self.namespace,
            self.target_pkg,
            decl_pxd,
            pxd,
            pyx,
            cpp,
            hpp).gen(ast)
            
        if not os.path.isdir(self.outdir):
            os.makedirs(self.outdir)
            
        with open(os.path.join(self.outdir, self.name + "_ext.py"), "w") as f:
            f.write(PyExtGenExtDef(self.name, self.target_pkg).gen(ast))
            
        with open(os.path.join(self.outdir, "%s_decl.pxd" % self.name), "w") as f:
            f.write(decl_pxd.content())
            
        with open(os.path.join(self.outdir, "%s.pxd" % self.name), "w") as f:
            f.write(pxd.content())
            
        with open(os.path.join(self.outdir, "%s.pyx" % self.name), "w") as f:
            f.write(pyx.content())
   
        with open(os.path.join(self.outdir, "PyBaseVisitor.h"), "w") as f:
            f.write(hpp.content())
            
        with open(os.path.join(self.outdir, "PyBaseVisitor.cpp"), "w") as f:
            f.write(cpp.content())

