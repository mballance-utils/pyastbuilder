'''
Created on Mar 21, 2021

@author: mballance
'''
from astbuilder.ast import Ast
from astbuilder.gen_cpp import GenCPP
from astbuilder.linker import Linker
from astbuilder.parser import Parser
import os

from astbuilder.cmds.util import find_yaml_files
from astbuilder.pyext_gen import PyExtGen


def gen(args):
    # Find the AST source files
    yaml_files = []    
    for d in args.astdir:
        yaml_files.extend(find_yaml_files(d))

    ast = Ast()        
    for file in yaml_files:
        with open(file) as f:
            ast = Parser(ast).parse(f)
        
    Linker().link(ast)
        
    if not hasattr(args, "license") or args.license is None:
        args.license = None
    else:
        if not os.path.exists(args.license):
            raise Exception("License file " + args.license + " does not exist")
        
    if not hasattr(args, "namespace"):
        args.namespace = None
        
    if not hasattr(args, "name") or args.name is None:
        args.name = "ast"
        
        
    if not hasattr(args, "o") or args.o is None:
        args.o = os.getcwd()
        
    if not hasattr(args, "package") or args.package is None:
        args.package = args.name

    PyExtGen(
        args.o, 
        args.name,
        args.package,
        args.license,
        args.namespace).generate(ast)
        