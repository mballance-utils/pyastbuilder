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
    gen_py_ext.add_argument("-astdir", nargs="+")
    gen_py_ext.add_argument("-o")
    gen_py_ext.add_argument("-license")
    gen_py_ext.add_argument("-namespace")
    gen_py_ext.add_argument("-name")
    gen_py_ext.add_argument("-package")

    return parser

def main():
    
    parser = getparser()
    
    args = parser.parse_args()
    
    args.func(args)
    

if __name__ == "__main__":
    main()
    
