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


class PyExtGen(Visitor):
    
    def __init__(self,
                 outdir,
                 name,
                 license,
                 namespace):
        self.outdir = outdir
        self.name = name
        self.license = license
        self.namespace = namespace

    def generate(self, ast):
        PyExtGenPyx(self.outdir, self.name, self.namespace).gen(ast)            
            
        with open(os.path.join(self.outdir, self.name + "_ext.py"), "w") as f:
            f.write(PyExtGenExtDef(self.name).gen(ast))
    

        
        