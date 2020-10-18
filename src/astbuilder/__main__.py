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

def find_json_files(path):
    ret = []
    if not os.path.isdir(path):
        raise Exception("Directory " + path + " doesn't exist")
    for f in os.listdir(path):
        print("File: " + f)
        if os.path.splitext(f)[1] == ".json":
            ret.append(os.path.join(path, f))
            print("Found file " + f)
    return ret


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-astdir", nargs="+")
    parser.add_argument("-o")
    parser.add_argument("-license")
    parser.add_argument("-namespace")
    parser.add_argument("-name")
    
    args = parser.parse_args()
  
    # Find the AST source files
    json_files = []    
    for d in args.astdir:
        json_files.extend(find_json_files(d))

    ast = Ast()        
    for file in json_files:
        ast = Parser(ast).parse(file)
        
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
    