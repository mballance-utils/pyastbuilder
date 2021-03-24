'''
Created on Sep 12, 2020

@author: ballance
'''
import argparse
import os
from astbuilder.parser import Parser
from astbuilder.gen_cpp import GenCPP
from astbuilder.ast import Ast
from astbuilder.linker import Linker
from astbuilder.cmds import gen_cpp
from astbuilder.cmds import gen_pyext

def find_yaml_files(path):
    ret = []
    if not os.path.isdir(path):
        raise Exception("Directory " + path + " doesn't exist")
    for f in os.listdir(path):
        print("File: " + f)
        if os.path.splitext(f)[1] == ".yaml":
            ret.append(os.path.join(path, f))
            print("Found file " + f)
    return ret

def getparser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    subparsers.required = True

    gen_cpp_cmd = subparsers.add_parser("gen-cpp",
        help="Generates C++ data structures")
    gen_cpp_cmd.set_defaults(func=gen_cpp.gen)
    
    gen_cpp_cmd.add_argument("-astdir", nargs="+")
    gen_cpp_cmd.add_argument("-o")
    gen_cpp_cmd.add_argument("-license")
    gen_cpp_cmd.add_argument("-namespace")
    gen_cpp_cmd.add_argument("-name")
    
    gen_py_ext = subparsers.add_parser("gen-pyext",
        help="Generates infrastructure for a Python extension")
    gen_py_ext.set_defaults(func=gen_pyext.gen)

    return parser

def main():
    
    parser = getparser()
    
    args = parser.parse_args()
  
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

    gen = GenCPP(
        args.o, 
        args.name,
        args.license,
        args.namespace)
    
    gen.generate(ast)
        
    

if __name__ == "__main__":
    main()
    
