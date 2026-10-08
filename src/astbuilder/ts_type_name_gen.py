'''
TypeScript type-name and default-value generation.

The C++ analogue is cpp_type_name_gen.py. TypeScript needs one thing C++ does
not: a *default value* per type, because every generated field is declared with
an initializer rather than being left uninitialized.

Keeping the two derivations in one place is deliberate. The type spelling and
its default have to agree about nullability -- a field typed `T` defaulted to
`null` does not compile under strictNullChecks, and a field typed `T | null`
defaulted to a value forces a null check on every reader. Deriving them
separately is how that goes wrong.
'''

from .ast_class import AstClass
from .ast_enum import AstEnum
from .ast_flags import AstFlags
from .ast_struct import AstStruct
from .type_scalar import TypeKind
from .visitor import Visitor


# TypeKind -> (TypeScript type, default literal)
#
# Every kind is listed. A generator that falls through to the C++ spelling is
# how `double` reached emitted TypeScript as the identifier `double`.
_SCALAR = {
    TypeKind.String:  ("string",  "''"),
    TypeKind.Bool:    ("boolean", "false"),
    TypeKind.Int8:    ("number",  "0"),
    TypeKind.Uint8:   ("number",  "0"),
    TypeKind.Int16:   ("number",  "0"),
    TypeKind.Uint16:  ("number",  "0"),
    TypeKind.Int32:   ("number",  "0"),
    TypeKind.Uint32:  ("number",  "0"),
    TypeKind.Int64:   ("number",  "0"),
    TypeKind.Uint64:  ("number",  "0"),
    TypeKind.Float32: ("number",  "0"),
    TypeKind.Float64: ("number",  "0"),
}


class TsTypeNameGen(Visitor):
    """Render a model type as a TypeScript type expression.

    `qualifier` is the namespace alias under which generated *classes* are
    visible at the emission site: '' inside classes.ts where they are in scope,
    and 'cls.' inside factory.ts which imports them as a namespace. It applies
    to class references only -- enums and flags carry their own prefixes, and
    primitives carry none.

    `bare` drops the trailing `| null` for positions that cannot be null: a
    list element type, where the list itself carries the absence.
    """

    def __init__(self, qualifier="", bare=False):
        super().__init__()
        self.out = ""
        self.qualifier = qualifier
        self.bare = bare

    def gen(self, t):
        self.out = ""
        t.accept(self)
        return self.out

    def visitTypeScalar(self, t):
        self.out += _SCALAR[t.t][0]

    def visitTypeList(self, t):
        # The element type is never nullable: `list<UP<Expr>>` is Expr[], not
        # (Expr | null)[]. A hole in the list is not something the C++ AST can
        # represent, so admitting one in TypeScript would invent a state.
        elem = TsTypeNameGen(self.qualifier, bare=True).gen(t.t)
        self.out += "%s[]" % elem

    def visitTypeMap(self, t):
        kt = TsTypeNameGen(self.qualifier, bare=True).gen(t.kt)
        vt = TsTypeNameGen(self.qualifier, bare=True).gen(t.vt)
        self.out += "Map<%s, %s>" % (kt, vt)

    def visitTypePointer(self, t):
        # Unique / Shared / Raw all collapse to `T | null`. TypeScript has no
        # ownership to model, and pretending otherwise would leak a C++ concept
        # into an API that cannot honour it.
        inner = TsTypeNameGen(self.qualifier, bare=True).gen(t.t)
        self.out += inner if self.bare else "%s | null" % inner

    def visitTypeUserDef(self, t):
        target = t.target
        if isinstance(target, AstEnum):
            self.out += "enums.%s" % t.name
        elif isinstance(target, AstFlags):
            self.out += "flags.%s" % t.name
        elif isinstance(target, AstStruct):
            # A struct is a VALUE in this AST -- `location` is declared
            # `type: Location`, never `UP<Location>` -- so it is always present
            # and never nullable. Typing it `Location | null` compiles and then
            # forces a null check onto every reader of `.location.lineno`.
            self.out += "%s%s" % (self.qualifier, t.name)
        else:
            # A bare class reference is a pointer in all but spelling: the
            # builder fills these in as it walks, so they start absent.
            self.out += "%s%s" % (self.qualifier, t.name) if self.bare \
                else "%s%s | null" % (self.qualifier, t.name)


class TsDefaultGen(Visitor):
    """Render the default initializer for a model type."""

    def __init__(self):
        super().__init__()
        self.out = ""

    def gen(self, t):
        self.out = ""
        t.accept(self)
        return self.out

    def visitTypeScalar(self, t):
        self.out += _SCALAR[t.t][1]

    def visitTypeList(self, t):
        self.out += "[]"

    def visitTypeMap(self, t):
        self.out += "new Map()"

    def visitTypePointer(self, t):
        self.out += "null"

    def visitTypeUserDef(self, t):
        target = t.target
        if isinstance(target, AstEnum):
            # First declared member, matching the 0-valued enum emitted in
            # enums.ts. An explicit `init:` overrides this -- see ts_init().
            self.out += "enums.%s.%s" % (t.name, target.values[0][0])
        elif isinstance(target, AstFlags):
            self.out += "flags.%s.None" % t.name
        elif isinstance(target, AstStruct):
            self.out += "mk%s()" % t.name
        else:
            self.out += "null"


def ts_init(d):
    """Translate an explicit `init:` from the schema into a TS expression.

    Returns None when there is no usable override and the type default should
    stand. The schema's inits are written for C++, so:

      * `Enum::Member` is C++ scope resolution -> `enums.Enum.Member`
      * a bare enum member name is resolved against the field's own enum type
      * `0` on a pointer field means the null pointer, not the number
      * trailing punctuation appears in the schema (`init: 0;`) and would be
        copied verbatim into the emitted TypeScript
    """
    init = d.init
    if init is None:
        return None
    init = str(init).strip().rstrip(";").strip()
    if init == "":
        return None

    from .type_pointer import TypePointer
    from .type_userdef import TypeUserDef

    if "::" in init:
        enum_name, member = init.split("::", 1)
        return "enums.%s.%s" % (enum_name, member)

    # A bare identifier naming a member of this field's own enum type.
    if isinstance(d.t, TypeUserDef) and isinstance(d.t.target, AstEnum):
        for name, _ in d.t.target.values:
            if name == init:
                return "enums.%s.%s" % (d.t.name, init)
        return None

    if isinstance(d.t, TypePointer):
        # C++ spells the null pointer `0`; TypeScript does not.
        return "null" if init in ("0", "NULL", "nullptr") else None

    if init in ("true", "false"):
        return init
    try:
        int(init)
        return init
    except ValueError:
        return None
