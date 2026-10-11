'''
`astbuilder gen-reflect` -- mirrors cmds/gen_census.py.
'''
import os

from astbuilder.ast import Ast
from astbuilder.cmds.util import find_yaml_files
from astbuilder.gen_reflect import GenReflect
from astbuilder.linker import Linker
from astbuilder.parser import Parser


def gen(args):
    yaml_files = []
    for d in args.astdir:
        yaml_files.extend(find_yaml_files(d))
    # Read in the same order gen-cpp reads them (unsorted): the class ids must
    # follow the order gen-cpp emits IVisitor's methods in.
    ast = Ast()
    for file in yaml_files:
        with open(file) as f:
            ast = Parser(ast).parse(f)

    Linker().link(ast)

    license = getattr(args, "license", None)
    if license is not None:
        if not os.path.exists(license):
            raise Exception("License file " + license + " does not exist")
        with open(license, "r") as f:
            license = f.read()

    GenReflect(args.o, args.namespace, license).generate(ast)
