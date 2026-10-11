'''
Projections: how one target API spells each part of a model.

A model is described once, in YAML. Each backend projects it into a language:
C++ interfaces (`IExprBin::getLhs()`), a Python extension
(`ExprBin.getLhs()`), TypeScript classes (`ExprBin.lhs`), the reflection
tables a rule engine reads (`node.lhs`). A Projection answers, for one of
those targets, what a class is called, how each field is read and written,
what type it has there, and whether the target exposes it at all.

Documentation is the main user (astbuilder.sphinx renders a table with one
column per projection), so the answers must be what the generated code really
contains. The C++ and Python projections therefore do not re-derive names:
they run the backend's own accessor generator for the one field, into memory,
and read back the declarations it emitted. A change to a generator changes
the documentation with it.

Third-party projections subclass Projection and are named by dotted path,
`package.module:ClassName` (see load_projection).
'''
import contextlib
import dataclasses as dc
import importlib
import io
import re
from typing import Dict, List, Optional

from .ast_class import AstClass
from .ast_enum import AstEnum
from .ast_flags import AstFlags
from .ast_struct import AstStruct
from .outstream import OutStream
from .type_list import TypeList
from .type_map import TypeMap
from .type_pointer import TypePointer, PointerKind
from .type_scalar import TypeScalar, TypeKind
from .type_userdef import TypeUserDef


@dc.dataclass(frozen=True)
class Access:
    """One way a projection reaches a field.

    `role` is what the access does:

        view    the field itself, as an attribute or a list view
        get     read the value
        set     replace the value
        list    read the whole list as a list
        item    read one list element, by index
        add     append a list element
        count   number of list elements
        has     test a map key
        at      read a map value, by key
        other   anything the classifier does not recognise

    `text` is how it is written in the target (`getImport(i)`), and `type`
    the value type it yields or takes, in the target's terms, when known.
    """
    role: str
    text: str
    type: Optional[str] = None


class Projection(object):
    """Base class. Subclasses override what differs; the defaults suit a
    target that uses the YAML's own names."""

    #: Short identifier, used in configuration (`"cpp"`).
    name = "base"
    #: Column heading in documentation (`"C++"`).
    label = "Base"

    def __init__(self, ast, **options):
        self.ast = ast
        self.options = options
        self._cache: Dict = {}

    # -- classes and enums ------------------------------------------------

    def class_name(self, cls) -> str:
        return cls.name

    def enum_value(self, enum, value: str) -> str:
        return "%s.%s" % (enum.name, value)

    # -- fields -----------------------------------------------------------

    def hidden(self, cls, field) -> Optional[str]:
        """Why the target does not expose `field`, or None if it does."""
        return None

    def accessors(self, cls, field) -> List[Access]:
        """Every way the target reaches `field`; empty when hidden."""
        key = (cls.name, field.name)
        if key not in self._cache:
            self._cache[key] = [] if self.hidden(cls, field) else self._accessors(cls, field)
        return self._cache[key]

    def _accessors(self, cls, field) -> List[Access]:
        return [Access("view", ".%s" % field.name, self.field_type(cls, field))]

    def field_type(self, cls, field) -> Optional[str]:
        return None

    def primary(self, cls, field) -> Optional[Access]:
        """The access a reader most likely wants: the read."""
        acc = self.accessors(cls, field)
        for role in ("view", "get", "list"):
            for a in acc:
                if a.role == role:
                    return a
        return acc[0] if acc else None


def _quiet(fn, *args):
    """Run a generator call, discarding the progress it prints."""
    with contextlib.redirect_stdout(io.StringIO()):
        fn(*args)


# ==========================================================================
# C++
# ==========================================================================

_CPP_DECL = re.compile(
    r"virtual\s+(?P<ret>.*?)\s*\b(?P<name>\w+)\((?P<args>[^)]*)\)\s*(?P<const>const)?\s*=\s*0;")


class CppProjection(Projection):
    """The generated C++ interfaces (`gen-cpp`): `I<Class>` with
    `get<Field>()`/`set<Field>(v)`. Option `namespace` (`pssp::ast`)
    qualifies class and enum names."""

    name = "cpp"
    label = "C++"

    def _ns(self):
        ns = self.options.get("namespace")
        return ns + "::" if ns else ""

    def class_name(self, cls):
        if isinstance(cls, AstClass):
            return "%sI%s" % (self._ns(), cls.name)
        return self._ns() + cls.name

    def enum_value(self, enum, value):
        return "%s%s::%s" % (self._ns(), enum.name, value)

    def _decls(self, cls, field):
        from .cpp_accessor_gen import CppAccessorGen
        out_h, out_ih, out_cpp = OutStream(), OutStream(), OutStream()
        _quiet(CppAccessorGen(out_h, out_ih, out_cpp, cls.name).gen, field)
        ret = []
        seen = set()
        for line in out_ih.content().split("\n"):
            m = _CPP_DECL.search(line)
            if m is None or m.group("name") in seen:
                # A collection has a const and a non-const getX(); the first
                # (const) one stands for both.
                continue
            seen.add(m.group("name"))
            ret.append(m)
        return ret

    def _accessors(self, cls, field):
        ret = []
        for m in self._decls(cls, field):
            name, args = m.group("name"), m.group("args").strip()
            if name.startswith("get"):
                ret.append(Access("get", "%s()" % name, m.group("ret").strip()))
            elif name.startswith("set"):
                ret.append(Access("set", "%s(%s)" % (name, args), None))
            else:
                ret.append(Access("other", "%s(%s)" % (name, args), None))
        return ret

    def field_type(self, cls, field):
        for a in self.accessors(cls, field):
            if a.role == "get":
                return a.type
        return None


# ==========================================================================
# Python (gen-pyext)
# ==========================================================================

_PY_DEF = re.compile(
    r"^\s*(?:cpdef|def)\s+(?:(?P<ret>[\w\[\], .]*?)\s+)?(?P<name>\w+)\(self(?:,\s*(?P<args>[^)]*))?\)")
_PYI_DEF = re.compile(
    r"^\s*def\s+(?P<name>\w+)\(self(?:,\s*(?P<args>[^)]*))?\)\s*(?:->\s*(?P<ret>.+?))?\s*:")

# Cython return types as Python sees them.
_CY_TYPES = {
    "bool": "bool", "str": "str",
    "int8_t": "int", "uint8_t": "int", "int16_t": "int", "uint16_t": "int",
    "int32_t": "int", "uint32_t": "int", "int64_t": "int", "uint64_t": "int",
    "float": "float", "double": "float",
}


def _py_args(args):
    """`int v, bool own` -> `v, own`: parameter names only."""
    if not args:
        return ""
    names = []
    for a in args.split(","):
        a = a.split("=")[0].split(":")[0].strip()
        names.append(a.split()[-1] if a else a)
    return ", ".join(names)


class PythonProjection(Projection):
    """The generated Python extension (`gen-pyext`): methods named as in its
    `.pyx`, typed from its `.pyi` where the stub has the method. Option
    `module` (`pssparser.ast`) qualifies class names."""

    name = "python"
    label = "Python"

    def class_name(self, cls):
        mod = self.options.get("module")
        return "%s.%s" % (mod, cls.name) if mod else cls.name

    def _emit(self, cls, field):
        from .pyext_accessor_gen import PyExtAccessorGen
        outs = [OutStream() for _ in range(4)]     # decl_pxd, pxd, pyx, pyi
        _quiet(PyExtAccessorGen(self.options.get("pyext_name", "ast"),
                                cls.name, *outs).gen, field)
        return outs[2].content(), outs[3].content()

    def _role(self, field, name, nargs):
        f = field.name
        if name == f:
            return "view"
        if name == f + "Has":
            return "has"
        if name == f + "At":
            return "at"
        if name.startswith("num"):
            return "count"
        if name.startswith("add"):
            return "add"
        if name.startswith("set"):
            return "set"
        if name.startswith("get"):
            if isinstance(field.t, TypeList):
                return "item" if nargs else "list"
            return "get"
        return "other"

    def _accessors(self, cls, field):
        pyx, pyi = self._emit(cls, field)
        stub = {}
        for line in pyi.split("\n"):
            m = _PYI_DEF.match(line)
            if m:
                stub[(m.group("name"), bool(m.group("args")))] = m.group("ret")
        ret = []
        for line in pyx.split("\n"):
            m = _PY_DEF.match(line)
            if m is None:
                continue
            name, args = m.group("name"), _py_args(m.group("args"))
            role = self._role(field, name, bool(args))
            t = stub.get((name, bool(args)))
            if t is None and role not in ("set", "add"):
                # No stub (scalar getters and map accessors have none): fall
                # back to the .pyx return type, which is a C type or a class.
                cy = (m.group("ret") or "").strip()
                if cy in _CY_TYPES:
                    t = _CY_TYPES[cy]
                elif cy in self.ast.class_m or cy in self.ast.struct_m:
                    t = cy
            if t in ("None", ""):
                t = None
            ret.append(Access(role, "%s(%s)" % (name, args), t))
        return ret

    def field_type(self, cls, field):
        for role in ("get", "list", "view", "at"):
            for a in self.accessors(cls, field):
                if a.role == role and a.type:
                    return a.type
        return None


# ==========================================================================
# TypeScript (gen-ts)
# ==========================================================================

class TsProjection(Projection):
    """The generated TypeScript classes (`gen-ts`): every field is a public
    property of the same name."""

    name = "ts"
    label = "TypeScript"

    def field_type(self, cls, field):
        from .ts_gen_params import field_type
        return field_type(field)


# ==========================================================================
# Reflection (gen-reflect)
# ==========================================================================

_REFLECT_SCALAR = {
    TypeKind.String: "string", TypeKind.Bool: "bool",
    TypeKind.Float32: "double", TypeKind.Float64: "double",
}


class ReflectProjection(Projection):
    """The reflection tables (`gen-reflect`) a rule engine reads by name:
    `node.<field>`. A map field has a table entry but no getter, so it is
    hidden. Types are named generically (a class name, `list<T>`, `int`);
    a rule language with its own type names subclasses this."""

    name = "reflect"
    label = "Reflection"

    def hidden(self, cls, field):
        if isinstance(field.t, TypeMap):
            return "maps are not readable through reflection"
        return None

    def _accessors(self, cls, field):
        return [Access("view", "node.%s" % field.name, self.field_type(cls, field))]

    def type_name(self, t):
        if isinstance(t, TypeScalar):
            return _REFLECT_SCALAR.get(t.t, "int")
        if isinstance(t, TypePointer):
            return self.type_name(t.t)
        if isinstance(t, TypeUserDef):
            return t.name
        if isinstance(t, TypeList):
            return "list<%s>" % self.type_name(t.t)
        if isinstance(t, TypeMap):
            return "map<%s, %s>" % (self.type_name(t.kt), self.type_name(t.vt))
        return None

    def field_type(self, cls, field):
        return self.type_name(field.t)


# ==========================================================================
# Registry
# ==========================================================================

BUILTIN = {
    p.name: p for p in (CppProjection, PythonProjection, TsProjection, ReflectProjection)
}


def load_projection(spec, ast, **options) -> Projection:
    """A projection from a built-in name (`"cpp"`) or a dotted path
    (`"package.module:ClassName"` or `"package.module.ClassName"`), with
    `options` passed to its constructor."""
    if isinstance(spec, type) and issubclass(spec, Projection):
        cls = spec
    elif spec in BUILTIN:
        cls = BUILTIN[spec]
    else:
        if ":" in spec:
            mod, _, attr = spec.partition(":")
        else:
            mod, _, attr = spec.rpartition(".")
        if not mod or not attr:
            raise ValueError("Unknown projection %r: not built in (%s) and not a "
                             "dotted path" % (spec, ", ".join(sorted(BUILTIN))))
        cls = getattr(importlib.import_module(mod), attr)
        if not (isinstance(cls, type) and issubclass(cls, Projection)):
            raise ValueError("%s is not a Projection subclass" % spec)
    return cls(ast, **options)


# ==========================================================================
# Checking a projection against generated code
# ==========================================================================

def _blocks(text, start_re):
    """Split generated source into {class name: its text}, a block running
    from one class header to the next."""
    ret = {}
    ms = list(re.finditer(start_re, text, re.M))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        ret[m.group(1)] = text[m.start():end]
    return ret


def check_generated(ast, proj, gen_dir) -> List[str]:
    """Problems found comparing what `proj` says about every field of `ast`
    with the files a backend generated into `gen_dir` (empty when they agree).

    `gen_dir` is laid out as gen-cpp (any depth, `I<Class>.h`), gen-pyext
    (`ast.pyx` or another `*.pyx`), gen-ts (`classes.ts`) or gen-reflect
    (`Reflect.cpp`) writes it, according to `proj.name`. It guards the step
    that is not shared with the generators: running one field's accessor
    generator alone, and reading its output back.
    """
    import pathlib
    gen_dir = pathlib.Path(gen_dir)
    problems = []

    def read(pattern):
        files = sorted(gen_dir.rglob(pattern))
        return "\n".join(f.read_text() for f in files), files

    if proj.name == "cpp":
        headers = {p.name: p for p in gen_dir.rglob("I*.h")}
        lookup = lambda c: headers.get("I%s.h" % c.name)
    elif proj.name == "python":
        text, _ = read("*.pyx")
        blocks = _blocks(text, r"^cdef class (\w+)")
    elif proj.name == "ts":
        text, _ = read("classes.ts")
        blocks = _blocks(text, r"^export class (\w+)")
    elif proj.name == "reflect":
        text, _ = read("Reflect.cpp")
    else:
        raise ValueError("no generated-code check for projection %r" % proj.name)

    for c in ast.classes:
        if proj.name == "cpp":
            h = lookup(c)
            if h is None:
                problems.append("%s: no generated I%s.h" % (c.name, c.name))
                continue
            body = h.read_text()
        elif proj.name in ("python", "ts"):
            body = blocks.get(c.name)
            if body is None:
                problems.append("%s: class not found in generated code" % c.name)
                continue
        for d in c.data:
            where = "%s.%s" % (c.name, d.name)
            acc = proj.accessors(c, d)
            if proj.name == "reflect":
                # A scalar or node field has a getter; a list has a size and
                # an element accessor instead; a map has neither.
                has_getter = any(("%s_%s_%s(" % (fn, c.name, d.name)) in text
                                 for fn in ("get", "size"))
                if has_getter != bool(acc):
                    problems.append("%s: projection %s it, but gen-reflect %s" % (
                        where, "exposes" if acc else "hides",
                        "can read it" if has_getter else "cannot read it"))
                continue
            if not acc:
                problems.append("%s: no accessors" % where)
            for a in acc:
                name = re.match(r"\.?(\w+)", a.text).group(1)
                if proj.name == "ts":
                    found = re.search(r"^\s+%s\s*:" % re.escape(name), body, re.M)
                else:
                    found = re.search(r"\b%s\(" % re.escape(name), body)
                if not found:
                    problems.append("%s: %s not in generated code" % (where, a.text))
    return problems
