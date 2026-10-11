'''
Graphviz views (astbuilder.diagrams): what each view includes, and that dot
accepts every one of them.
'''
import shutil
import subprocess

import pytest

from astbuilder import diagrams
from unit.test_relations import _rel


def _dot_ok(text):
    if shutil.which("dot") is None:
        pytest.skip("graphviz is not installed")
    r = subprocess.run(["dot", "-Tsvg"], input=text, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _views(r):
    c = r.ast.class_m
    return {
        "inheritance": diagrams.inheritance(r, c["Node"]),
        "inheritance-depth": diagrams.inheritance(r, c["Node"], depth=1),
        "inheritance-max": diagrams.inheritance(r, c["Node"], max_children=1),
        "containment": diagrams.containment(r, c["Root"], depth=2),
        "neighbourhood": diagrams.neighbourhood(r, c["Expr"]),
        "map": diagrams.model_map(r),
        "legend": diagrams.legend(),
    }


@pytest.mark.parametrize("view", ["inheritance", "inheritance-depth", "inheritance-max",
                                  "containment", "neighbourhood", "map", "legend"])
def test_dot_accepts(view):
    _dot_ok(_views(_rel())[view])


def test_inheritance_limits():
    r = _rel()
    full = diagrams.inheritance(r, r.ast.class_m["Node"])
    assert '"ExprBin"' in full
    shallow = diagrams.inheritance(r, r.ast.class_m["Node"], depth=1)
    assert '"ExprBin"' not in shallow
    assert "+2 below" in shallow          # Expr's two subclasses
    capped = diagrams.inheritance(r, r.ast.class_m["Node"], max_children=1)
    assert "+2 more" in capped            # Node has three subclasses


def test_containment_styles():
    r = _rel()
    text = diagrams.containment(r, r.ast.class_m["Root"], depth=2)
    assert 'label="decls[*]"' in text
    assert 'label="index{key}"' in text
    assert "style=dashed" in text          # Decl.uses
    assert 'color="#888888"' in text       # Node.parent, a back-pointer
    assert 'label="Node (+6)"' in text     # an edge to a base names its subclass count


def test_containment_without_refs():
    r = _rel()
    text = diagrams.containment(r, r.ast.class_m["Root"], depth=2, refs=False)
    assert "style=dashed" not in text


def test_neighbourhood():
    r = _rel()
    text = diagrams.neighbourhood(r, r.ast.class_m["ExprRef"])
    assert '"Expr" -> "ExprRef"' in text   # base
    assert '"ExprRef" -> "Decl"' in text   # target
    assert '"Decl" -> "ExprRef"' in text   # Decl.uses is declared as ExprRef


def test_urls():
    r = _rel()
    text = diagrams.neighbourhood(r, r.ast.class_m["Expr"], url=lambda c: "#%s" % c.name)
    assert 'URL="#Expr"' in text
    svg = _dot_ok(text)
    assert 'href="#Expr"' in svg


def test_map_groups_by_file():
    r = _rel()
    text = diagrams.model_map(r)
    assert '"model"' in text
    assert "9 classes" in text


def test_map_refs_are_optional():
    from astbuilder.parser import Parser
    from astbuilder.ast import Ast
    from astbuilder.linker import Linker
    from astbuilder.relations import Relations
    import io
    ast = Ast()
    Parser(ast, "a.yaml").parse(io.StringIO("classes:\n  - A:\n      data:\n        - b: P<B>\n"))
    Parser(ast, "b.yaml").parse(io.StringIO("classes:\n  - B\n"))
    Linker().link(ast)
    r = Relations(ast)
    assert "->" not in diagrams.model_map(r)
    assert '"a" -> "b"' in diagrams.model_map(r, refs=True)
    assert "1 class\"" in diagrams.model_map(r)
