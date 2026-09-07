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
from astbuilder.cmds import gen_ts
from astbuilder.cmds import gen_wasm



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

    gen_ts_cmd = subparsers.add_parser("gen-ts",
        help="Generates TypeScript data structures")
    gen_ts_cmd.set_defaults(func=gen_ts.gen)
    gen_ts_cmd.add_argument("-astdir", nargs="+")
    gen_ts_cmd.add_argument("-o")
    gen_ts_cmd.add_argument("-license")
    # No -namespace or -name: TypeScript scopes by module, so both would be
    # accepted and ignored.
    gen_ts_cmd.add_argument("--no-visitor", action="store_true",
        help="Omit visitor.ts and the accept() method on each class")

    gen_wasm_cmd = subparsers.add_parser("gen-wasm",
        help="Generates the C++/TypeScript AST serialisation pair")
    gen_wasm_cmd.set_defaults(func=gen_wasm.gen)
    gen_wasm_cmd.add_argument("-astdir", nargs="+")
    # Two required outputs rather than one -o. The halves land in different
    # trees -- the C++ beside the WASM build, the TypeScript beside the classes
    # it constructs -- and defaulting either to the cwd would let one be
    # regenerated without the other, which is the one thing this backend exists
    # to prevent.
    gen_wasm_cmd.add_argument("-cpp", required=True,
        help="Directory to write AstSerializer.{h,cpp} into")
    gen_wasm_cmd.add_argument("-ts", required=True,
        help="Directory to write deserialize.ts into (the gen-ts output tree)")
    gen_wasm_cmd.add_argument("-license")

    return parser

def main():
    
    parser = getparser()
    
    args = parser.parse_args()
    
    args.func(args)
    

if __name__ == "__main__":
    main()
    
