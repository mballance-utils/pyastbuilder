'''
Parser: the documentation-only parts of the schema.

Field docs, enum and flags value docs, source locations, and the `rel:` and
`set_by:` attributes. None of these changes generated code; they exist for the
documentation tooling (astbuilder.sphinx) and for error messages.
'''
import io

import pytest

from astbuilder.ast import Ast
from astbuilder.linker import Linker
from astbuilder.parser import Parser


def _load(doc, filename="model.yaml"):
    ast = Ast()
    Parser(ast, filename).parse(io.StringIO(doc))
    Linker().link(ast)
    return ast


def _field(ast, cls, name):
    return next(d for d in ast.class_m[cls].data if d.name == name)


# --------------------------------------------------------------------------
# Field docs
# --------------------------------------------------------------------------

def test_field_doc_list_form_stays_on_the_field():
    # The list form used to assign a field's doc to its *class*, replacing the
    # class's own doc.
    ast = _load("""
classes:
  - Node:
      doc: The class doc.
      data:
        - count:
          - doc: How many.
          - type: int32_t
""")
    assert ast.class_m["Node"].doc == "The class doc."
    assert _field(ast, "Node", "count").doc == "How many."


def test_field_doc_mapping_form():
    # The mapping form used to reject `doc:`.
    ast = _load("""
classes:
  - Node:
      data:
        - count:
            type: int32_t
            doc: How many.
""")
    assert _field(ast, "Node", "count").doc == "How many."


def test_field_without_doc():
    ast = _load("""
classes:
  - Node:
      data:
        - count: int32_t
""")
    assert _field(ast, "Node", "count").doc is None


def test_docs_are_plain_str():
    # The loader tags strings with their line; what reaches a generator must
    # be an ordinary str.
    ast = _load("""
classes:
  - Node:
      doc: The class doc.
      data:
        - count:
            type: int32_t
            doc: How many.
""")
    assert type(ast.class_m["Node"].doc) is str
    assert type(_field(ast, "Node", "count").doc) is str
    assert type(ast.class_m["Node"].name) is str


# --------------------------------------------------------------------------
# Enum and flags values
# --------------------------------------------------------------------------

def test_enum_value_forms():
    ast = _load("""
enums:
  - Op:
    - Add
    - Sub: Subtraction
    - Mul:
        doc: Multiplication
    - Div:
""")
    e = ast.enum_m["Op"]
    # `values` keeps the shape the generators read.
    assert e.values == [("Add", None), ("Sub", None), ("Mul", None), ("Div", None)]
    assert e.value_docs == {"Sub": "Subtraction", "Mul": "Multiplication"}
    assert all(type(v[0]) is str for v in e.values)


def test_flags_value_forms():
    ast = _load("""
flags:
  - Attr:
    - Rand
    - Const: Constant
""")
    f = ast.flags_m["Attr"]
    assert f.values == ["Rand", "Const"]
    assert f.value_docs == {"Const": "Constant"}


def test_enum_explicit_value_is_rejected():
    with pytest.raises(Exception, match="explicit value"):
        _load("""
enums:
  - Op:
    - Add:
        value: 4
""")


def test_enum_unknown_value_key():
    with pytest.raises(Exception, match="unknown value key"):
        _load("""
enums:
  - Op:
    - Add:
        dox: typo
""")


# --------------------------------------------------------------------------
# Source locations
# --------------------------------------------------------------------------

def test_source_locations():
    ast = _load("""\
enums:
  - Op:
    - Add
    - Sub: Subtraction
classes:
  - Base
  - Node:
      super: Base
      data:
        - count: int32_t
""")
    assert (ast.enum_m["Op"].srcfile, ast.enum_m["Op"].srcline) == ("model.yaml", 2)
    assert ast.enum_m["Op"].value_lines == {"Add": 3, "Sub": 4}
    assert ast.class_m["Base"].srcline == 6
    assert ast.class_m["Node"].srcline == 7
    assert _field(ast, "Node", "count").srcline == 10
    assert _field(ast, "Node", "count").srcfile == "model.yaml"


def test_filename_from_stream_name(tmp_path):
    p = tmp_path / "x.yaml"
    p.write_text("classes:\n  - Node\n")
    ast = Ast()
    with open(p) as f:
        Parser(ast).parse(f)
    assert ast.class_m["Node"].srcfile == str(p)


def test_error_names_file_and_line():
    with pytest.raises(Exception, match=r"model\.yaml:6"):
        _load("""\
classes:
  - Node:
      data:
        - count:
            type: int32_t
            bogus: 1
""")


# --------------------------------------------------------------------------
# rel: and set_by:
# --------------------------------------------------------------------------

def test_rel_and_set_by():
    ast = _load("""
classes:
  - Scope:
      data:
        - children: list<UP<Scope>>
  - Child:
      set_by: linker
      data:
        - parent:
            type: P<Scope>
            rel: parent
        - peers:
            type: list<P<Child>>
            rel: ref
        - target:
            type: P<Scope>
            set_by: linker
""")
    assert ast.class_m["Child"].set_by == "linker"
    assert ast.class_m["Scope"].set_by is None
    assert _field(ast, "Child", "parent").rel == "parent"
    assert _field(ast, "Child", "peers").rel == "ref"
    assert _field(ast, "Child", "target").rel is None
    assert _field(ast, "Child", "target").set_by == "linker"
    assert _field(ast, "Scope", "children").set_by is None


@pytest.mark.parametrize("ftype", ["UP<Scope>", "list<UP<Scope>>", "int32_t"])
def test_rel_only_on_raw_pointers(ftype):
    with pytest.raises(Exception, match="applies only to P<T>"):
        _load("""
classes:
  - Scope:
      data:
        - f:
            type: %s
            rel: parent
""" % ftype)


def test_rel_value_checked():
    with pytest.raises(Exception, match="must be one of"):
        _load("""
classes:
  - Scope:
      data:
        - f:
            type: P<Scope>
            rel: owner
""")


def test_doc_lines():
    # A block scalar's text starts on the line after `|`; a plain scalar's on
    # its own line.
    ast = _load("""\
enums:
  - Op:
    - Add: Addition
classes:
  - Node:
      doc: |
          The class doc.
      data:
        - count:
            type: int32_t
            doc: How many.
""")
    assert ast.class_m["Node"].docline == 7
    assert _field(ast, "Node", "count").docline == 11
    assert ast.enum_m["Op"].value_doclines == {"Add": 3}


# --------------------------------------------------------------------------
# Enum and flags docs
# --------------------------------------------------------------------------

def test_enum_doc_mapping_form():
    ast = _load("""
enums:
  - Color:
      doc: The colours.
      values:
        - Red: "Warm"
        - Blue
flags:
  - Attr:
      doc: The attributes.
      values:
        - Rand
        - Const: "Read-only"
""")
    e = ast.enum_m["Color"]
    assert e.doc == "The colours." and e.docline == 4
    assert e.values == [("Red", None), ("Blue", None)]
    assert e.value_docs == {"Red": "Warm"}
    f = ast.flags_m["Attr"]
    assert f.doc == "The attributes."
    assert f.values == ["Rand", "Const"] and f.value_docs == {"Const": "Read-only"}


def test_enum_list_form_has_no_doc():
    ast = _load("""
enums:
  - Color:
      - Red
""")
    assert ast.enum_m["Color"].doc is None
    assert ast.enum_m["Color"].values == [("Red", None)]


@pytest.mark.parametrize("body,msg", [
    ("      doc: x\n      vals: [A]\n", "unknown key vals"),
    ("      doc: x\n", "values: must be a list"),
    ("      Red\n", "expected a list of values"),
])
def test_enum_mapping_form_errors(body, msg):
    with pytest.raises(Exception, match=msg):
        _load("enums:\n  - Color:\n" + body)
