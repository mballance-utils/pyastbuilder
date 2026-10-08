'''
`astbuilder gen-wasm` -- mirrors cmds/gen_ts.py.
'''
import os

from astbuilder.ast import Ast
from astbuilder.cmds.util import find_yaml_files
from astbuilder.gen_wasm import GenWasm
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

    # Both halves are required. Emitting one without the other is the state
    # this backend exists to make impossible -- a serializer and a deserializer
    # that came from different schema revisions.
    GenWasm(args.cpp, args.ts, license).generate(ast)
