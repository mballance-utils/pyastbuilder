'''
astbuilder.sphinx: build a small project with `sphinx -W` and check what it
renders, links and refuses.
'''
import os
import re
import shutil
import subprocess
import sys
import textwrap

import pytest

pytest.importorskip("sphinx")

from unit.test_relations import MODEL

CONF = '''
extensions = ["astbuilder.sphinx"]
astbuilder_models = {"m": {
    "yaml": ["model/*.yaml"],
    "projections": [{"projection": "cpp", "namespace": "m::ast"}, "python", "ts", "reflect"],
    "roots": ["Root"],
    "phases": [("parser", "Set by the parser"), ("linker", "Set by the linker")],
    %(extra)s
}}
'''

INDEX = '''
Model
=====

.. toctree::

   ref

See :astb:class:`ExprBin`, :astb:field:`Decl.init` and :astb:enumvalue:`Op.Add`.

.. astb:model-map::

.. astb:legend::

.. astb:inheritance-tree:: Node
   :depth: 1

.. astb:inheritance-diagram:: Node

.. astb:containment-diagram:: Root
   :depth: 2

.. astb:neighbourhood:: Decl

.. astb:relations-table:: Decl

.. astb:projection-table:: ExprBin
'''

REF = '''
Reference
=========

.. astb:model::
   :group: model
'''


def _project(tmp_path, index=INDEX, extra=""):
    src = tmp_path / "src"
    (src / "model").mkdir(parents=True)
    model = MODEL.replace("    - Add\n", "    - Add: Addition, ``a + b``\n", 1)
    model = model.replace("  - Orphan:\n", "  - Orphan:\n      doc: |\n          Held by nothing.\n", 1)
    (src / "model" / "model.yaml").write_text(model)
    (src / "conf.py").write_text(CONF % {"extra": extra})
    (src / "index.rst").write_text(textwrap.dedent(index))
    (src / "ref.rst").write_text(textwrap.dedent(REF))
    return src


def _build(src, out, warn_error=True):
    args = [sys.executable, "-m", "sphinx", "-b", "html", "-q"]
    if warn_error:
        args.append("-W")
    r = subprocess.run(args + [str(src), str(out)], capture_output=True, text=True)
    return r


def _text(html):
    import html as _html
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if shutil.which("dot") is None:
        pytest.skip("graphviz is not installed")
    tmp = tmp_path_factory.mktemp("sphinx")
    src = _project(tmp)
    out = tmp / "out"
    r = _build(src, out)
    assert r.returncode == 0, r.stderr
    return out


def test_entries_and_anchors(built):
    ref = (built / "ref.html").read_text()
    for anchor in ("astb-class-ExprBin", "astb-field-ExprBin-lhs", "astb-enum-Op",
                   "astb-enumvalue-Op-Add", "astb-class-Orphan"):
        assert 'id="%s"' % anchor in ref, anchor
    text = _text(ref)
    assert "Held by nothing." in text                  # class doc:
    assert "Addition," in text                         # enum value doc:
    assert "refers to (set by linker)" in text         # set_by:
    assert "back-pointer to" in text                   # rel: parent


def test_relationships_in_class_entry(built):
    text = _text((built / "ref.html").read_text())
    i = text.index("class ExprBin")
    entry = text[i:text.index("class ExprRef")]
    assert "Inherits: Node › Expr › ExprBin" in entry
    assert "As itself: Decl.init" in entry
    assert "Through Expr : ExprBin.lhs , ExprBin.rhs" in entry
    assert "Root → Root.decls → Decl.init" in entry
    assert "getLhs()" in entry and "node.lhs" in entry


def test_roles_resolve_across_pages(built):
    index = (built / "index.html").read_text()
    assert 'href="ref.html#astb-class-ExprBin"' in index
    assert 'href="ref.html#astb-field-Decl-init"' in index
    assert 'href="ref.html#astb-enumvalue-Op-Add"' in index


def test_diagrams_link_to_entries(built):
    svgs = list((built / "_images").glob("*.svg"))
    assert len(svgs) >= 5
    linked = [s for s in svgs if "astb-class-Decl" in s.read_text()]
    assert linked, "no diagram links to the Decl entry"
    # Links are rewritten relative to _images/, and name the page.
    assert any("../ref.html#astb-class-Decl" in s.read_text() for s in linked)


def test_model_map_links_groups(built):
    svgs = [s.read_text() for s in (built / "_images").glob("*.svg")]
    assert any("ref.html#astb-group-m-model" in s for s in svgs)


def test_inheritance_tree_depth(built):
    text = _text((built / "index.html").read_text())
    assert "Expr (+2 below)" in text


def test_dangling_role_fails_a_W_build(tmp_path):
    src = _project(tmp_path, index=INDEX + "\nAlso :astb:class:`NoSuchClass`.\n")
    r = _build(src, tmp_path / "out")
    assert r.returncode != 0
    assert "NoSuchClass" in r.stderr


def test_unknown_directive_target(tmp_path):
    src = _project(tmp_path, index=INDEX + "\n.. astb:class:: NoSuchClass\n")
    r = _build(src, tmp_path / "out")
    assert r.returncode != 0
    assert "no class named 'NoSuchClass'" in r.stderr


def test_paths_can_be_turned_off(tmp_path):
    src = _project(tmp_path, extra='"paths": False,')
    out = tmp_path / "out"
    r = _build(src, out, warn_error=False)
    assert r.returncode == 0, r.stderr
    assert "Containment" not in _text((out / "ref.html").read_text())


def test_doc_warning_points_at_yaml(tmp_path):
    src = _project(tmp_path)
    y = src / "model" / "model.yaml"
    y.write_text(y.read_text().replace(
        "Held by nothing.", "Held by nothing.\n\n          Broken `reference <.\n"))
    r = _build(src, tmp_path / "out", warn_error=False)
    assert "model.yaml:" in r.stderr
    # The warning names the line of the doc text, not the page that includes it.
    line = int(re.search(r"model\.yaml:(\d+)", r.stderr).group(1))
    assert "Broken" in (src / "model" / "model.yaml").read_text().split("\n")[line - 1]


def test_unknown_phase_is_a_warning(tmp_path):
    src = _project(tmp_path)
    y = src / "model" / "model.yaml"
    y.write_text(y.read_text().replace("set_by: linker", "set_by: linkr"))
    r = _build(src, tmp_path / "out")
    assert r.returncode != 0
    assert "'linkr' is not a configured phase" in r.stderr


def test_coverage_notes():
    from astbuilder.sphinx import Model, model_report
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "model"))
        with open(os.path.join(d, "model", "model.yaml"), "w") as f:
            f.write(MODEL)
        m = Model("m", {"yaml": ["model/*.yaml"], "roots": ["Root"],
                        "phases": [("parser", ""), ("linker", "")]}, d)
    warnings, notes = model_report(m)
    assert warnings == []
    assert any("classes no root contains: Orphan" in n for n in notes)
    assert any("P<T> fields have no rel:" in n and "ExprRef.target" in n for n in notes)


def test_coverage_notes_count_enums(tmp_path):
    from astbuilder.sphinx import Model, model_report
    (tmp_path / "model.yaml").write_text("""
enums:
  - Documented:
      doc: The documented one.
      values:
        - A: "First"
        - B
  - Bare:
      - C: "Third"
classes:
  - Root:
      doc: The root.
""")
    m = Model("m", {"yaml": ["model.yaml"], "roots": ["Root"]}, str(tmp_path))
    _, notes = model_report(m)
    assert "1 of 2 enums and flags and 1 of 3 values have no description" in notes


def test_diagrams_have_text_forms(built):
    text = _text((built / "index.html").read_text())
    assert "Class Field Relationship Holds" in text          # containment table
    assert "Root Root.decls owns a list of Decl" in text
    assert "back-pointer: a dotted grey line" in text        # legend
    assert "Decl.uses refers to ExprRef" in text             # neighbourhood table


def test_no_text_option(tmp_path):
    if shutil.which("dot") is None:
        pytest.skip("graphviz is not installed")
    src = _project(tmp_path, index="T\n=\n\n.. toctree::\n\n   ref\n\n"
                   ".. astb:containment-diagram:: Root\n   :no-text:\n")
    out = tmp_path / "out"
    r = _build(src, out)
    assert r.returncode == 0, r.stderr
    assert "Holds" not in _text((out / "index.html").read_text())


def test_doc_sections(tmp_path):
    src = _project(tmp_path, extra='"doc_backticks": "literal",')
    y = src / "model" / "model.yaml"
    y.write_text(y.read_text().replace("""  - Decl:
      super: Node
""", """  - Decl:
      super: Node
      doc: |
          A declaration with an `init` value.

          Attributes:
              init: The initial value
              parent: The scope that declares it

          See Also:
              ExprRef, Root.decls
              the linker, for uses
"""))
    out = tmp_path / "out"
    r = _build(src, out)
    assert r.returncode == 0, r.stderr
    html = (out / "ref.html").read_text()
    text = _text(html)
    start = text.index("class Decl")
    entry = text[start:text.index("class Expr ", start)]
    assert "<code" in html and "A declaration with an init value." in entry
    assert "Attributes:" not in entry                       # taken out of the body
    assert "init UP< ExprBin > owns The initial value" in entry
    assert "As described for Decl : parent : The scope that declares it" in entry   # inherited field
    assert "See also: ExprRef , Root.decls ; the linker, for uses" in entry
    assert 'href="#astb-field-Root-decls"' in html
    assert (out / "_static" / "astb.css").exists()


def test_model_map_list_links_groups(built):
    index = (built / "index.html").read_text()
    assert 'href="ref.html#astb-group-m-model"' in index


def test_struct_and_enum_docs_split_like_class_docs(tmp_path):
    # A struct's Attributes: entries describe its fields in the fields table
    # (a multi-line entry used to reach reST verbatim and break -W), and an
    # enum's See Also: links like a class's.
    src = tmp_path / "src"
    (src / "model").mkdir(parents=True)
    (src / "model" / "model.yaml").write_text("""
enums:
  - Kind:
      doc: |
          What a Pos points at.

          See Also:
              Pos
      values:
        - Here
structs:
  - Pos:
      doc: |
          A position.

          Attributes:
              line: The line, counted
                  from 1.
      data:
        - line: int32_t
        - col:
            type: int32_t
            doc: The column.
classes:
  - Root:
      doc: The root.
      data:
        - at: Pos
""")
    (src / "conf.py").write_text(CONF % {"extra": ""})
    (src / "index.rst").write_text("T\n=\n\n.. astb:model:: m\n   :no-diagram:\n")
    r = _build(src, tmp_path / "out")
    assert r.returncode == 0, r.stderr
    text = _text((tmp_path / "out" / "index.html").read_text())
    assert "line int32_t The line, counted from 1." in text
    assert "col int32_t The column." in text
    assert "Attributes" not in text
    assert "See also: Pos" in text
