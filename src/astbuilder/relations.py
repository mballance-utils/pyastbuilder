'''
The relationships in a model: inheritance, containment, references.

Built from a parsed and linked Ast, with no Sphinx dependency, so the
documentation (astbuilder.sphinx), the `astbuilder relations` command and
tests all read the same graph.

Each field whose value is a node, or a list or map of nodes, is an Edge:

    owns        UP<T> / SP<T>             one child, owned
    owns-list   list<UP<T>>, map<K,UP<T>> many children, owned
    refs        P<T>, list<P<T>>          a node owned elsewhere
    back        P<T> with `rel: parent`   the inverse of containment

A field of a struct, enum, flags or scalar type is a `value` edge (target is
the struct/enum/flags, or None for a scalar). An edge to T means "T or any
subclass of T": the graph keeps the declared type, and subclass expansion is
a separate query, so a view can say "any of 27 Expr kinds" instead of drawing
27 edges.

This is a *schema-level* view. At run time a few owning lists also hold nodes
another list owns (pssparser's `extend` members listed again in a template
body); the schema cannot say so, and the field's `doc:` must.
'''
import collections
import dataclasses as dc
from typing import Dict, List, Optional

from .ast_class import AstClass
from .ast_enum import AstEnum
from .ast_flags import AstFlags
from .ast_struct import AstStruct
from .type_list import TypeList
from .type_map import TypeMap
from .type_pointer import TypePointer, PointerKind
from .type_scalar import TypeScalar
from .type_userdef import TypeUserDef

OWNS = "owns"
OWNS_LIST = "owns-list"
REFS = "refs"
BACK = "back"
VALUE = "value"

#: Edge kinds that make up the containment tree.
CONTAINMENT = (OWNS, OWNS_LIST)
#: Edge kinds whose target is a class.
NODE_KINDS = (OWNS, OWNS_LIST, REFS, BACK)


@dc.dataclass(frozen=True)
class Edge:
    """One field, seen as a relationship from its declaring class."""
    cls: object          # the AstClass (or AstStruct) declaring the field
    field: object        # the AstData
    kind: str            # OWNS, OWNS_LIST, REFS, BACK or VALUE
    target: object       # AstClass / AstStruct / AstEnum / AstFlags, or None
    many: bool           # a list or map of them
    keyed: bool = False  # a map

    @property
    def label(self):
        """`Scope.children`"""
        return "%s.%s" % (self.cls.name, self.field.name)


def _classify(field, t, many=False, keyed=False):
    """(kind, target, many, keyed) for a field of type `t`."""
    if isinstance(t, TypePointer):
        tgt = t.t.target if isinstance(t.t, TypeUserDef) else None
        if t.pt == PointerKind.Raw:
            kind = BACK if getattr(field, "rel", None) == "parent" else REFS
        else:
            kind = OWNS_LIST if many else OWNS
        return kind, tgt, many, keyed
    if isinstance(t, TypeList):
        return _classify(field, t.t, True, keyed)
    if isinstance(t, TypeMap):
        return _classify(field, t.vt, True, True)
    if isinstance(t, TypeUserDef):
        tgt = t.target
        if isinstance(tgt, AstClass):
            # A class held by value: not something the generators produce
            # for nodes, but treat it as owned.
            return (OWNS_LIST if many else OWNS), tgt, many, keyed
        return VALUE, tgt, many, keyed
    return VALUE, None, many, keyed


class Relations(object):

    def __init__(self, ast, roots=()):
        self.ast = ast
        self._sub: Dict[str, List] = collections.defaultdict(list)
        for c in ast.classes:
            if c.super is not None and c.super.target is not None:
                self._sub[c.super.target.name].append(c)
        for v in self._sub.values():
            v.sort(key=lambda c: c.name)
        self.roots = []
        for r in roots:
            if r not in ast.class_m:
                raise ValueError("root %s is not a class of the model" % r)
            self.roots.append(ast.class_m[r])
        self._edges = {}
        for c in list(ast.classes) + list(ast.structs):
            self._edges[c.name] = [Edge(c, d, *_classify(d, d.t)) for d in c.data]
        self._paths = None

    # -- inheritance --------------------------------------------------------

    def superclass(self, c) -> Optional[AstClass]:
        return c.super.target if getattr(c, "super", None) is not None else None

    def ancestors(self, c) -> List[AstClass]:
        """Parent first, root last."""
        ret = []
        a = self.superclass(c)
        while a is not None:
            ret.append(a)
            a = self.superclass(a)
        return ret

    def subclasses(self, c) -> List[AstClass]:
        """Direct subclasses, by name."""
        return list(self._sub.get(c.name, ()))

    def descendants(self, c) -> List[AstClass]:
        """Every class deriving from `c`, depth first, excluding `c`."""
        ret = []
        for s in self.subclasses(c):
            ret.append(s)
            ret.extend(self.descendants(s))
        return ret

    def is_a(self, c, base) -> bool:
        return c is base or base in self.ancestors(c)

    def inheritance_roots(self) -> List[AstClass]:
        return sorted((c for c in self.ast.classes if self.superclass(c) is None),
                      key=lambda c: c.name)

    # -- fields as edges ----------------------------------------------------

    def edges(self, c, inherited=False) -> List[Edge]:
        """The fields `c` declares as edges; with `inherited`, its ancestors'
        too, nearest ancestor last."""
        ret = list(self._edges.get(c.name, ()))
        if inherited:
            for a in self.ancestors(c):
                ret.extend(self._edges.get(a.name, ()))
        return ret

    def edge(self, c, field) -> Edge:
        for e in self._edges.get(c.name, ()):
            if e.field is field:
                return e
        raise KeyError("%s.%s" % (c.name, field.name))

    def all_edges(self, kinds=NODE_KINDS) -> List[Edge]:
        return [e for c in self.ast.classes for e in self._edges.get(c.name, ())
                if e.kind in kinds]

    def set_by(self, c, field, default=None) -> Optional[str]:
        """The phase that fills `field`: its own `set_by:`, else its class's,
        else `default`."""
        return getattr(field, "set_by", None) or getattr(c, "set_by", None) or default

    # -- the reverse: where a class can appear --------------------------------

    def appears_in(self, c, kinds=NODE_KINDS):
        """Fields that can hold a `c`.

        Returns (direct, via_base): `direct` are edges whose declared target
        is `c`; `via_base` is [(ancestor, edges), ...], nearest ancestor
        first, for the edges declared with that ancestor as their target.
        """
        direct = []
        by_target = collections.defaultdict(list)
        for e in self.all_edges(kinds):
            if e.target is not None:
                by_target[e.target.name].append(e)
        direct = sorted(by_target.get(c.name, ()), key=lambda e: e.label)
        via_base = []
        for a in self.ancestors(c):
            es = by_target.get(a.name)
            if es:
                via_base.append((a, sorted(es, key=lambda e: e.label)))
        return direct, via_base

    # -- containment ---------------------------------------------------------

    def _owned_targets(self, c):
        """(edge, class, generality) triples: every class an instance of `c`
        can own directly, through its own or inherited fields, with subclass
        expansion of each edge's declared type. `generality` is how many
        inheritance steps the class is below the edge's declared type."""
        for e in self.edges(c, inherited=True):
            if e.kind in CONTAINMENT and isinstance(e.target, AstClass):
                yield e, e.target, 0
                for d in self.descendants(e.target):
                    yield e, d, len(self.ancestors(d)) - len(self.ancestors(e.target))

    def _compute_paths(self):
        # Cheapest path per root. Each step costs 1 plus its generality: a
        # field declared as exactly the class it holds is preferred over one
        # declared as a distant base. With plain hop counts a model whose
        # scopes hold `list<UP<ScopeChild>>` reaches nearly every class in
        # one step from the root, which is true and says nothing. Ties break
        # on names, so the paths are stable.
        import heapq
        self._paths = {}
        for r in self.roots:
            prev = {r.name: None}
            best = {r.name: 0}
            heap = [(0, r.name)]
            while heap:
                cost, cname = heapq.heappop(heap)
                if cost > best.get(cname, cost):
                    continue
                c = self.ast.class_m[cname]
                for e, t, gen in sorted(self._owned_targets(c),
                                        key=lambda p: (p[0].label, p[1].name)):
                    nc = cost + 1 + gen
                    if t.name not in best or nc < best[t.name]:
                        best[t.name] = nc
                        prev[t.name] = (c, e)
                        heapq.heappush(heap, (nc, t.name))
            self._paths[r.name] = prev

    def containment_path(self, c, root) -> Optional[List]:
        """The shortest chain of owning fields from `root` to an instance of
        `c`, as [(edge, class reached), ...]; [] when `c` is `root`, None when
        `root` cannot reach `c`."""
        if self._paths is None:
            self._compute_paths()
        prev = self._paths[root.name]
        if c.name not in prev:
            return None
        ret = []
        n = c
        while prev[n.name] is not None:
            p, e = prev[n.name]
            ret.append((e, n))
            n = p
        ret.reverse()
        return ret

    def containment_paths(self, c) -> Dict[str, List]:
        """{root name: path} for every root that reaches `c`."""
        ret = collections.OrderedDict()
        for r in self.roots:
            p = self.containment_path(c, r)
            if p is not None:
                ret[r.name] = p
        return ret

    def unreachable(self) -> List[AstClass]:
        """Classes no root can contain, by name. Empty when there are no roots.

        Abstract bases are reachable whenever one of their subclasses is
        held by a field typed as the base; a class listed here appears in no
        owning field at all (it may still be referenced, or be a root of its
        own that was not configured)."""
        if not self.roots:
            return []
        if self._paths is None:
            self._compute_paths()
        seen = set()
        for prev in self._paths.values():
            seen.update(prev)
        return sorted((c for c in self.ast.classes if c.name not in seen), key=lambda c: c.name)

    # -- export ----------------------------------------------------------------

    def to_json(self):
        """A plain-data form of the graph, for `astbuilder relations`."""
        def name(x):
            return x.name if x is not None else None
        classes = []
        for c in sorted(self.ast.classes, key=lambda c: c.name):
            classes.append({
                "name": c.name,
                "super": name(self.superclass(c)),
                "subclasses": [s.name for s in self.subclasses(c)],
                "file": c.srcfile,
                "line": c.srcline,
                "set_by": c.set_by,
                "fields": [{
                    "name": e.field.name,
                    "kind": e.kind,
                    "target": name(e.target),
                    "many": e.many,
                    "keyed": e.keyed,
                    "rel": e.field.rel,
                    "set_by": e.field.set_by,
                } for e in self.edges(c)],
                "paths": {r: [e.label for e, _ in p]
                          for r, p in self.containment_paths(c).items()},
            })
        return {
            "roots": [r.name for r in self.roots],
            "classes": classes,
            "unreachable": [c.name for c in self.unreachable()],
        }
