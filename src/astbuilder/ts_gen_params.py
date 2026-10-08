'''
Constructor-parameter generation for the TypeScript backend.

A direct analogue of cpp_gen_params.py, and the recursion order is the point:
base-class parameters come FIRST, then the class's own. The C++ factory is the
contract -- `mkActivityParallel("", spec)` passes SymbolScope's `name` before
ActivityParallel's own `join_spec` -- and a TypeScript factory that ordered
them differently would silently mean something else at every call site.
'''

from .ts_type_name_gen import TsDefaultGen, TsTypeNameGen, ts_init


def ctor_fields(c):
    """Constructor fields for `c`, base-first, as a flat list of AstData."""
    ret = []
    if c.super is not None and c.super.target is not None:
        ret.extend(ctor_fields(c.super.target))
    ret.extend([d for d in c.data if d.is_ctor])
    return ret


def own_ctor_fields(c):
    return [d for d in c.data if d.is_ctor]


def inherited_ctor_fields(c):
    if c.super is None or c.super.target is None:
        return []
    return ctor_fields(c.super.target)


def field_type(d, qualifier=""):
    """The declared TypeScript type of a field, wide enough for its default."""
    return TsTypeNameGen(qualifier).gen(d.t)


def field_default(d):
    """The initializer for a field: an explicit `init:` if usable, else the
    type's own default."""
    override = ts_init(d)
    return override if override is not None else TsDefaultGen().gen(d.t)


def ctor_params(c, qualifier=""):
    """`name: Type = default` for every constructor parameter, base-first.

    EVERY parameter carries a default. The C++ factory requires all arguments;
    this AST is also built incrementally by hand-written consumers that
    construct a node and then assign fields as they walk. Defaulting makes the
    generated API a superset of the C++ one rather than forcing an edit at each
    such site, while leaving order and arity identical.
    """
    return ["%s: %s = %s" % (d.name, field_type(d, qualifier), field_default(d))
            for d in ctor_fields(c)]
