'''
Created on Mar 22, 2021

@author: mballance
'''
from astbuilder.outstream import OutStream

class PyExtGenExtDef(object):
    """Generates the extension-definition python file"""
    
    def __init__(self,
                 name,
                 package):
        self.name = name
        self.package = package
        pass
    
    def gen(self, ast):
        self.out = OutStream()
        
        self.out.println("import os")
        self.out.println("from setuptools import Extension")
        self.out.println("def ext():")
        self.out.inc_indent()
        self.out.println("extdir = os.path.dirname(os.path.abspath(__file__))")
        self.out.println("return Extension(\"%s\", [" % self.package)
        self.out.inc_indent()
        self.out.inc_indent()
        # TODO: list files and patterns
        self.out.println("os.path.join(extdir, '%s.pyx'), os.path.join(extdir, 'PyBaseVisitor.cpp')" % self.name)
        self.out.dec_indent()
        self.out.println("],")
        self.out.println("include_dirs=[extdir],")
        self.out.println("language=\"c++\")")
        self.out.dec_indent()
        self.out.dec_indent()
        
        return self.out.content()