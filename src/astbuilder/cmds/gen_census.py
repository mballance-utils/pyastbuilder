'''
`astbuilder gen-census` -- mirrors cmds/gen_wasm.py.
'''
import os

from astbuilder.ast import Ast
from astbuilder.cmds.util import find_yaml_files
from astbuilder.gen_census import GenCensus
from astbuilder.linker import Linker
from astbuilder.parser import Parser


def gen(args):
    yaml_files = []
    for d in args.astdir:
        yaml_files.extend(find_yaml_files(d))

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

    # Both halves are required, for gen-wasm's reason: a census that describes
    # the native AST is worth nothing without the one that describes the
    # deserialised tree, and two emitted from different schema revisions would
    # disagree everywhere and mean nothing.
    GenCensus(args.py, args.ts, license).generate(ast)
