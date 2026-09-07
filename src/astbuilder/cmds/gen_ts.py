'''
`astbuilder gen-ts` -- mirrors cmds/gen_cpp.py.
'''
import os

from astbuilder.ast import Ast
from astbuilder.cmds.util import find_yaml_files
from astbuilder.gen_ts import GenTS
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

    outdir = getattr(args, "o", None) or os.getcwd()

    GenTS(
        outdir,
        license,
        gen_visitor=not getattr(args, "no_visitor", False),
    ).generate(ast)
