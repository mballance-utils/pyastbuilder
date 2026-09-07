'''
Unit tests for the TypeScript backend (gen_ts).

These drive the generator on small schemas and assert on the emitted source.
Every case here is a defect that actually occurred in a hand-written TypeScript
generator that this backend replaces -- asserting on the text is what pins each
one, because most are invisible from outside until a consumer happens to have
the shape that triggers them.
'''
import io
import os
import tempfile

from astbuilder.ast import Ast
from astbuilder.gen_ts import GenTS
from astbuilder.linker import Linker
from astbuilder.parser import Parser


def _gen(doc):
    """Generate TypeScript for `doc` and return {filename: content}."""
    ast = Ast()
    Parser(ast).parse(io.StringIO(doc))
    Linker().link(ast)
    with tempfile.TemporaryDirectory() as d:
        GenTS(d).generate(ast)
        return {f: open(os.path.join(d, f)).read() for f in os.listdir(d)}


def _cls(src, name):
    """The body of `export class <name> ...` up to its closing brace."""
    start = src.index("export class %s " % name)
    return src[start:src.index("\n}", start)]


# --------------------------------------------------------------------------
# Constructor chaining
# --------------------------------------------------------------------------

def test_super_ctor_args_are_chained():
    """A subclass must pass its base's ctor fields to super().

    An unconditional `super()` is correct only when no ancestor takes
    arguments. It compiles for a schema where that happens to hold and breaks
    wholesale when one is added.
    """
    out = _gen("""
classes:
    - Base:
        data:
            - name: string
    - Derived:
        super: Base
        data:
            - count: int32_t
""")
    body = _cls(out["classes.ts"], "Derived")
    assert "super(name);" in body
    # Base-first, matching the C++ factory's argument order.
    assert "constructor(name: string = '', count: number = 0)" in body


def test_factory_takes_the_whole_chain():
    out = _gen("""
classes:
    - Base:
        data:
            - name: string
    - Derived:
        super: Base
        data:
            - count: int32_t
""")
    assert "mkDerived(name: string = '', count: number = 0): cls.Derived" \
        in out["factory.ts"]
    assert "return new cls.Derived(name, count);" in out["factory.ts"]


# --------------------------------------------------------------------------
# Type mapping
# --------------------------------------------------------------------------

def test_float_is_a_number():
    """`double` must not reach the emitted TypeScript as an identifier."""
    out = _gen("""
classes:
    - HasFloat:
        data:
            - value: double
            - single: float
""")
    body = _cls(out["classes.ts"], "HasFloat")
    assert "value: number = 0;" in body
    assert "single: number = 0;" in body
    assert "double" not in body


def test_struct_field_is_a_value_not_a_pointer():
    """A struct-typed field is always present and defaults to mk<Struct>().

    Typing it `T | null` compiles, and then forces a null check onto every
    reader of the field.
    """
    out = _gen("""
structs:
    - Location:
        data:
            - lineno: int32_t
classes:
    - Node:
        data:
            - location: Location
""")
    body = _cls(out["classes.ts"], "Node")
    assert "location: Location = mkLocation();" in body
    assert "location: Location | null" not in body


def test_pointer_field_is_nullable():
    out = _gen("""
classes:
    - Expr:
        data:
            - id: int32_t
    - Holder:
        data:
            - expr:
                - type: UP<Expr>
                - is_ctor: false
""")
    assert "expr: Expr | null = null;" in _cls(out["classes.ts"], "Holder")


def test_list_elements_are_not_nullable():
    """`list<UP<T>>` is T[], not (T | null)[] -- a hole in the list is not a
    state the source AST can represent."""
    out = _gen("""
classes:
    - Item:
        data:
            - id: int32_t
    - Bag:
        data:
            - items: list<UP<Item>>
""")
    assert "items: Item[] = [];" in _cls(out["classes.ts"], "Bag")


def test_uninitialized_bool_defaults_to_false():
    """A non-ctor bool with no explicit `init:` must still be initialized."""
    out = _gen("""
classes:
    - Flagged:
        data:
            - is_standalone:
                - type: bool
                - is_ctor: false
""")
    assert "is_standalone: boolean = false;" in _cls(out["classes.ts"], "Flagged")


# --------------------------------------------------------------------------
# Imports and qualification
# --------------------------------------------------------------------------

def test_structs_file_imports_enums_when_it_needs_them():
    """structs.ts has no other reason to import anything, so the one case that
    needs an import is the one that gets forgotten."""
    out = _gen("""
enums:
    - Kind:
        - First
        - Second
structs:
    - Elem:
        data:
            - kind: Kind
""")
    assert "import * as enums from './enums';" in out["structs.ts"]
    assert "kind: enums.Kind" in out["structs.ts"]


def test_factory_qualifies_parameter_types_not_just_returns():
    """factory.ts sees classes only through a namespace import, so a bare class
    name in a *parameter* position resolves to nothing."""
    out = _gen("""
classes:
    - Expr:
        data:
            - id: int32_t
    - Holder:
        data:
            - expr: UP<Expr>
""")
    line = [l for l in out["factory.ts"].split("\n") if "mkHolder(" in l][0]
    assert "cls.Expr | null" in line, line


# --------------------------------------------------------------------------
# Schema shapes
# --------------------------------------------------------------------------

def test_list_form_class_body_is_parsed():
    """A class body written as a LIST of single-key maps carries the same
    meaning as the mapping form.

    pssparser's constraint.yaml uses this form throughout. A generator that
    reads `body['data']` without handling it emits the class with no fields and
    no superclass -- silently, and it still compiles.
    """
    out = _gen("""
classes:
    - Stmt:
        data:
            - id: int32_t
    - SoftStmt:
        - super: Stmt
        - data:
            - expr: int32_t
""")
    body = _cls(out["classes.ts"], "SoftStmt")
    assert "export class SoftStmt extends Stmt" in body
    assert "expr: number = 0;" in body


def test_enum_init_is_translated_from_cpp_scope_resolution():
    out = _gen("""
enums:
    - Form:
        - None_
        - Block
classes:
    - Doc:
        data:
            - form:
                - type: Form
                - is_ctor: false
                - init: Form::Block
""")
    assert "form: enums.Form = enums.Form.Block;" in _cls(out["classes.ts"], "Doc")


def test_trailing_punctuation_in_init_is_not_copied_through():
    """The schema contains `init: 0;`. Emitting it verbatim produces a syntax
    error; emitting `0` for a pointer produces a type error. It means null."""
    out = _gen("""
classes:
    - Field:
        data:
            - id: int32_t
    - Ref:
        data:
            - it:
                - type: P<Field>
                - is_ctor: false
                - init: 0;
""")
    body = _cls(out["classes.ts"], "Ref")
    assert "it: Field | null = null;" in body
    assert ";;" not in body
