'''
The relationship graph (astbuilder.relations): edges, inheritance queries,
"appears in", containment paths and unreachable classes.
'''
import io
import json

import pytest

from astbuilder.ast import Ast
from astbuilder.linker import Linker
from astbuilder.parser import Parser
from astbuilder.relations import (BACK, OWNS, OWNS_LIST, REFS, VALUE,
                                  Relations)

MODEL = """
enums:
  - Op:
    - Add
classes:
  - Node:
      data:
        - parent:
            type: P<Scope>
            rel: parent
  - Scope:
      super: Node
      data:
        - children: list<UP<Node>>
  - Root:
      super: Scope
      data:
        - decls: list<UP<Decl>>
  - Expr:
      super: Node
  - ExprBin:
      super: Expr
      data:
        - op: Op
        - lhs: UP<Expr>
        - rhs: UP<Expr>
  - ExprRef:
      super: Expr
      data:
        - target:
            type: P<Decl>
            set_by: linker
  - Decl:
      super: Node
      data:
        - init: UP<ExprBin>
        - uses: list<P<ExprRef>>
        - index: map<string,UP<Entry>>
  - Entry:
      data:
        - name: string
  - Orphan:
      data:
        - count: int32_t
"""


def _rel(roots=("Root",)):
    ast = Ast()
    Parser(ast, "model.yaml").parse(io.StringIO(MODEL))
    Linker().link(ast)
    return Relations(ast, roots=roots)


def _c(r, name):
    return r.ast.class_m[name]


def _names(cs):
    return [c.name for c in cs]


def test_edge_kinds():
    r = _rel()
    kinds = {e.field.name: (e.kind, e.target.name if e.target else None, e.many, e.keyed)
             for c in r.ast.classes for e in r.edges(c)}
    assert kinds["parent"] == (BACK, "Scope", False, False)
    assert kinds["children"] == (OWNS_LIST, "Node", True, False)
    assert kinds["lhs"] == (OWNS, "Expr", False, False)
    assert kinds["target"] == (REFS, "Decl", False, False)
    assert kinds["uses"] == (REFS, "ExprRef", True, False)
    assert kinds["index"] == (OWNS_LIST, "Entry", True, True)
    assert kinds["op"] == (VALUE, "Op", False, False)
    assert kinds["count"] == (VALUE, None, False, False)


def test_inheritance():
    r = _rel()
    assert _names(r.ancestors(_c(r, "ExprBin"))) == ["Expr", "Node"]
    assert _names(r.subclasses(_c(r, "Node"))) == ["Decl", "Expr", "Scope"]
    assert _names(r.descendants(_c(r, "Node"))) == [
        "Decl", "Expr", "ExprBin", "ExprRef", "Scope", "Root"]
    assert _names(r.inheritance_roots()) == ["Entry", "Node", "Orphan"]
    assert r.is_a(_c(r, "Root"), _c(r, "Node"))
    assert not r.is_a(_c(r, "Node"), _c(r, "Root"))


def test_inherited_edges():
    r = _rel()
    assert [e.label for e in r.edges(_c(r, "Root"), inherited=True)] == [
        "Root.decls", "Scope.children", "Node.parent"]


def test_set_by():
    r = _rel()
    c = _c(r, "ExprRef")
    assert r.set_by(c, c.data[0], default="parser") == "linker"
    c = _c(r, "ExprBin")
    assert r.set_by(c, c.data[0], default="parser") == "parser"


def test_appears_in():
    r = _rel()
    direct, via = r.appears_in(_c(r, "ExprBin"))
    assert [e.label for e in direct] == ["Decl.init"]
    assert [(a.name, [e.label for e in es]) for a, es in via] == [
        ("Expr", ["ExprBin.lhs", "ExprBin.rhs"]),
        ("Node", ["Scope.children"]),
    ]
    direct, via = r.appears_in(_c(r, "ExprRef"))
    assert [e.label for e in direct] == ["Decl.uses"]


def test_containment_paths_prefer_specific_fields():
    # Through `children` (declared Node) ExprBin is one step away but two
    # inheritance levels below the declared type: cost 3. Through `decls`
    # and `init`, both declared as exactly what they hold, it costs 2.
    r = _rel()
    p = r.containment_path(_c(r, "ExprBin"), _c(r, "Root"))
    assert [(e.label, c.name) for e, c in p] == [
        ("Root.decls", "Decl"), ("Decl.init", "ExprBin")]
    assert r.containment_path(_c(r, "Root"), _c(r, "Root")) == []


def test_containment_through_a_map():
    r = _rel()
    p = r.containment_path(_c(r, "Entry"), _c(r, "Root"))
    assert [e.label for e, _ in p] == ["Root.decls", "Decl.index"]


def test_unreachable():
    r = _rel()
    assert _names(r.unreachable()) == ["Orphan"]
    assert r.containment_paths(_c(r, "Orphan")) == {}
    assert _rel(roots=()).unreachable() == []


def test_unknown_root():
    with pytest.raises(ValueError):
        _rel(roots=("NoSuch",))


def test_to_json():
    r = _rel()
    j = json.loads(json.dumps(r.to_json()))
    assert j["roots"] == ["Root"]
    assert j["unreachable"] == ["Orphan"]
    expr_bin = next(c for c in j["classes"] if c["name"] == "ExprBin")
    assert expr_bin["super"] == "Expr"
    assert expr_bin["file"] == "model.yaml"
    assert expr_bin["paths"] == {"Root": ["Root.decls", "Decl.init"]}
    assert {f["name"]: f["kind"] for f in expr_bin["fields"]} == {
        "op": "value", "lhs": "owns", "rhs": "owns"}
