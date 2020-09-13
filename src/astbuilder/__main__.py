'''
Created on Sep 12, 2020

@author: ballance
'''
import argparse
import os
from astgen.parser import Parser
from astgen.gen_cpp import GenCPP

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
    
    args = parser.parse_args()
  
    # Find the AST source files
    json_files = []    
    for d in args.astdir:
        json_files.extend(find_json_files(d))
        
    for file in json_files:
        ast = Parser().parse(file)
        
    if not hasattr(args, "o") or args.o is None:
        args.o = "foo"

    gen = GenCPP(args.o)
    
    gen.generate(ast)
        
    

if __name__ == "__main__":
    main()
    