'''
Projections (astbuilder.projection): what each target calls each field.

The answers are checked two ways: by value on a small model, for the shapes
whose spelling matters (plural lists, maps, enums), and against code the real
backends generate for the same model (check_generated), for every field.
'''
import contextlib
import io

import pytest

from astbuilder.ast import Ast
from astbuilder.gen_cpp import GenCPP
from astbuilder.gen_reflect import GenReflect
from astbuilder.gen_ts import GenTS
from astbuilder.linker import Linker
from astbuilder.parser import Parser
from astbuilder.projection import (Access, Projection, ReflectProjection,
                                   check_generated, load_projection)
from astbuilder.pyext_gen import PyExtGen

# One field of each shape the generators treat differently.
MODEL = """
enums:
  - Op:
    - Add
    - Sub
flags:
  - Attr:
    - Rand
structs:
  - Loc:
      data:
        - line: int32_t
classes:
  - Node:
      data:
        - parent: P<Scope>
  - Scope:
      super: Node
      data:
        - children: list<UP<Node>>
        - path: list<UP<Node>>
        - refs: list<P<Node>>
        - names: list<string>
        - locs: list<Loc>
        - symtab: map<string,int32_t>
  - Leaf:
      super: Node
      data:
        - name: string
        - count: int32_t
        - flag: bool
        - op: Op
        - attr: Attr
        - loc: Loc
        - child: UP<Node>
"""


def _ast():
    ast = Ast()
    Parser(ast, "model.yaml").parse(io.StringIO(MODEL))
    Linker().link(ast)
    return ast


def _acc(proj, cls, field):
    c = proj.ast.class_m[cls]
    d = next(x for x in c.data if x.name == field)
    return [(a.role, a.text, a.type) for a in proj.accessors(c, d)]


# --------------------------------------------------------------------------
# By value
# --------------------------------------------------------------------------

def test_cpp():
    p = load_projection("cpp", _ast(), namespace="m::ast")
    assert p.class_name(p.ast.class_m["Leaf"]) == "m::ast::ILeaf"
    assert p.enum_value(p.ast.enum_m["Op"], "Add") == "m::ast::Op::Add"
    assert _acc(p, "Leaf", "count") == [
        ("get", "getCount()", "int32_t"), ("set", "setCount(int32_t v)", None)]
    # A collection has a const and a non-const getter; one entry stands for both.
    assert [r for r, _, _ in _acc(p, "Scope", "children")] == ["get"]


def test_python_list_spellings():
    p = load_projection("python", _ast(), module="m.ast")
    assert p.class_name(p.ast.class_m["Scope"]) == "m.ast.Scope"
    # `children` reads as a plural: getChildren() / getChild(i).
    assert _acc(p, "Scope", "children") == [
        ("view", "children()", "ListUtil[Node]"),
        ("list", "getChildren()", "List[Node]"),
        ("item", "getChild(i)", "Node"),
        ("add", "addChild(i)", None),
        ("count", "numChildren()", "int"),
    ]
    # `path` does not: getPathList() / getPath(i).
    roles = {r: t for r, t, _ in _acc(p, "Scope", "path")}
    assert roles["list"] == "getPathList()"
    assert roles["item"] == "getPath(i)"


def test_python_scalar_has_no_stub_but_is_typed():
    # Scalar getters have no .pyi stub; the type comes from the .pyx.
    p = load_projection("python", _ast())
    assert _acc(p, "Leaf", "count") == [("get", "getCount()", "int")]
    assert _acc(p, "Leaf", "op") == [("get", "getOp()", "int"), ("set", "setOp(v)", None)]


def test_python_map():
    p = load_projection("python", _ast())
    assert _acc(p, "Scope", "symtab") == [
        ("has", "symtabHas(i)", "bool"), ("at", "symtabAt(i)", "int")]


def test_ts():
    p = load_projection("ts", _ast())
    assert _acc(p, "Leaf", "count") == [("view", ".count", "number")]
    assert _acc(p, "Scope", "children") == [("view", ".children", "Node[]")]


def test_reflect_hides_maps():
    p = load_projection("reflect", _ast())
    c = p.ast.class_m["Scope"]
    symtab = next(x for x in c.data if x.name == "symtab")
    assert p.accessors(c, symtab) == []
    assert "map" in p.hidden(c, symtab)
    assert _acc(p, "Scope", "children") == [("view", "node.children", "list<Node>")]
    assert _acc(p, "Leaf", "op") == [("view", "node.op", "Op")]


def test_primary():
    p = load_projection("python", _ast())
    c = p.ast.class_m["Scope"]
    d = next(x for x in c.data if x.name == "children")
    assert p.primary(c, d).text == "children()"


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

class _Custom(ReflectProjection):
    name = "custom"
    label = "Custom"


def test_load_by_dotted_path():
    # Compared by name: pytest imports this file as `test_projection`, and the
    # dotted path imports it again as `unit.test_projection`.
    ast = _ast()
    assert type(load_projection("unit.test_projection:_Custom", ast)).__name__ == "_Custom"
    assert type(load_projection("unit.test_projection._Custom", ast)).__name__ == "_Custom"
    assert isinstance(load_projection(_Custom, ast), _Custom)


def test_load_rejects_non_projection():
    with pytest.raises(ValueError):
        load_projection("unit.test_projection:MODEL", _ast())
    with pytest.raises(ValueError):
        load_projection("nosuch", _ast())


# --------------------------------------------------------------------------
# Against generated code
# --------------------------------------------------------------------------

def _generate(kind, ast, d):
    with contextlib.redirect_stdout(io.StringIO()):
        if kind == "cpp":
            GenCPP(str(d), "ast", None, "m::ast").generate(ast)
        elif kind == "python":
            PyExtGen(str(d), "ast", "m.ast", None, "m::ast").generate(ast)
        elif kind == "ts":
            GenTS(str(d)).generate(ast)
        elif kind == "reflect":
            GenReflect(str(d), "m::ast").generate(ast)


@pytest.mark.parametrize("kind", ["cpp", "python", "ts", "reflect"])
def test_agrees_with_generated_code(kind, tmp_path):
    ast = _ast()
    _generate(kind, ast, tmp_path)
    proj = load_projection(kind, ast, namespace="m::ast")
    assert check_generated(ast, proj, tmp_path) == []


def test_check_generated_reports_a_mismatch(tmp_path):
    ast = _ast()
    _generate("ts", ast, tmp_path)

    class Wrong(Projection):
        name = "ts"

        def _accessors(self, cls, field):
            return [Access("view", ".no_such_%s" % field.name)]

    problems = check_generated(ast, Wrong(ast), tmp_path)
    assert problems and "not in generated code" in problems[0]
