'''
`astbuilder relations` -- the model's relationship graph, as JSON or as a
Graphviz view (astbuilder.relations, astbuilder.diagrams).
'''
import json
import sys

from astbuilder import diagrams
from astbuilder.ast import Ast
from astbuilder.cmds.util import find_yaml_files
from astbuilder.linker import Linker
from astbuilder.parser import Parser
from astbuilder.relations import Relations


def load(astdirs):
    ast = Ast()
    for d in astdirs:
        for file in sorted(find_yaml_files(d)):
            with open(file) as f:
                Parser(ast).parse(f)
    Linker().link(ast)
    return ast


def gen(args):
    ast = load(args.astdir)
    rel = Relations(ast, roots=args.root or ())

    if args.format == "json":
        text = json.dumps(rel.to_json(), indent=2) + "\n"
    else:
        view = args.view
        cls = None
        if view in ("inheritance", "containment", "neighbourhood"):
            if not args.cls:
                sys.exit("--view %s needs --class" % view)
            if args.cls not in ast.class_m:
                sys.exit("unknown class %s" % args.cls)
            cls = ast.class_m[args.cls]
        if view == "inheritance":
            text = diagrams.inheritance(rel, cls, depth=args.depth)
        elif view == "containment":
            text = diagrams.containment(rel, cls, depth=args.depth or 1)
        elif view == "neighbourhood":
            text = diagrams.neighbourhood(rel, cls)
        elif view == "map":
            text = diagrams.model_map(rel)
        else:
            text = diagrams.legend()

    if args.o:
        with open(args.o, "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
