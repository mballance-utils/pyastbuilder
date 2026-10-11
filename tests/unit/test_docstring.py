'''astbuilder.docstring: splitting Google-style sections out of a class doc.'''
from astbuilder.docstring import backticks_to_literal, names, split

DOC = """Root of a resolved symbol tree.

PSS Example::

    component c { }

Attributes:
    units: Compilation units linked
        into this tree
    filenames (map): Maps file IDs to paths

See Also:
    SymbolScope, GlobalScope.children
    the linker (for how units are merged)
"""


def test_split():
    p = split(DOC)
    assert p.body == "Root of a resolved symbol tree.\n\nPSS Example::\n\n    component c { }"
    assert p.attributes == {"units": "Compilation units linked into this tree",
                            "filenames": "Maps file IDs to paths"}
    assert p.see_also == ["SymbolScope, GlobalScope.children",
                          "the linker (for how units are merged)"]


def test_split_without_sections():
    assert split("Just text.").body == "Just text."
    assert split(None).body == ""


def test_names():
    assert names("SymbolScope, GlobalScope.children") == ["SymbolScope", "GlobalScope.children"]
    assert names("the linker (for how units are merged)") == []
    assert names("the linker, for uses") == []
    assert names("Expr.") == ["Expr"]


def test_backticks():
    assert backticks_to_literal("the `name` field") == "the ``name`` field"
    assert backticks_to_literal("already ``lit``") == "already ``lit``"
    assert backticks_to_literal(":astb:class:`Expr` and `a link`_") == \
        ":astb:class:`Expr` and `a link`_"


def test_backticks_leave_literal_blocks():
    text = "Use `x`::\n\n    a = `raw`;\n\nThen `y`."
    assert backticks_to_literal(text) == "Use ``x``::\n\n    a = `raw`;\n\nThen ``y``."
