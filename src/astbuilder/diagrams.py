'''
Graphviz (DOT) views of a model's relationships.

Every view is *scoped*: an inheritance tree below one class, what one class
contains, one class's neighbourhood, or the model map (one node per YAML
file). A whole-model graph of a real schema (pssparser: 229 classes) cannot
be read, so there is none.

Conventions, shared by every view and drawn once by legend():

    inherits     hollow triangle at the base class (UML)
    owns         solid line, filled arrow
    owns-list    solid line, filled arrow, field labelled `name[*]`
                 (`name{key}` for a map)
    refs         dashed line, open arrow
    back         dotted grey line, open arrow

A node whose class has subclasses is labelled "Expr (+27)": an edge to a
class means that class or any subclass.

`url` is a function from a class to a link (or None), which makes the SVG
nodes clickable; astbuilder.sphinx passes one that resolves to the class's
entry.
'''
import os
from typing import Callable, Optional

from .ast_class import AstClass
from .relations import BACK, OWNS, OWNS_LIST, REFS, Relations

_FONT = 'fontname="Helvetica", fontsize=10'

_EDGE_STYLE = {
    OWNS: 'style=solid, arrowhead=normal',
    OWNS_LIST: 'style=solid, arrowhead=normal',
    REFS: 'style=dashed, arrowhead=vee',
    BACK: 'style=dotted, arrowhead=vee, color="#888888", fontcolor="#888888"',
}


def _q(s):
    return '"%s"' % str(s).replace("\\", "\\\\").replace('"', '\\"')


class _Graph(object):

    def __init__(self, name, rankdir="LR", url=None):
        self.lines = []
        self.nodes = {}
        self.url = url
        self.lines.append("digraph %s {" % _q(name))
        self.lines.append('  graph [rankdir=%s, bgcolor="transparent", %s];' % (rankdir, _FONT))
        self.lines.append('  node [shape=box, style="rounded", height=0.3, %s];' % _FONT)
        self.lines.append('  edge [fontname="Helvetica", fontsize=9];')

    def node(self, key, label, cls=None, extra=""):
        if key in self.nodes:
            return
        self.nodes[key] = True
        attrs = ["label=%s" % _q(label)]
        if cls is not None and self.url is not None:
            u = self.url(cls)
            if u:
                attrs.append("URL=%s" % _q(u))
                attrs.append('target="_top"')
                attrs.append("tooltip=%s" % _q(cls.name))
        if extra:
            attrs.append(extra)
        self.lines.append("  %s [%s];" % (_q(key), ", ".join(attrs)))

    def edge(self, a, b, attrs):
        self.lines.append("  %s -> %s [%s];" % (_q(a), _q(b), attrs))

    def text(self):
        return "\n".join(self.lines + ["}"]) + "\n"


def _class_label(rel, c):
    n = len(rel.descendants(c))
    return "%s (+%d)" % (c.name, n) if n else c.name


def _edge_label(e):
    if e.keyed:
        return "%s{key}" % e.field.name
    if e.many:
        return "%s[*]" % e.field.name
    return e.field.name


def inheritance(rel: Relations, root, depth: Optional[int] = None,
                url: Callable = None, max_children: int = 0) -> str:
    """The classes below `root`, to `depth` levels (all when None). With
    `max_children`, a class shows at most that many subclasses and one
    "+N more" node for the rest."""
    g = _Graph("inheritance_%s" % root.name, rankdir="LR", url=url)
    g.lines.append('  edge [dir=back, arrowtail=empty];')

    def walk(c, level):
        g.node(c.name, c.name, c, 'style="rounded,bold"' if c is root else "")
        if depth is not None and level >= depth:
            n = len(rel.descendants(c))
            if n:
                key = "%s.more" % c.name
                g.node(key, "+%d below" % n, None, 'shape=plaintext')
                g.edge(c.name, key, 'style=dotted')
            return
        subs = rel.subclasses(c)
        shown = subs[:max_children] if max_children and len(subs) > max_children else subs
        for s in shown:
            walk(s, level + 1)
            g.edge(c.name, s.name, "")
        if len(shown) < len(subs):
            key = "%s.rest" % c.name
            g.node(key, "+%d more" % (len(subs) - len(shown)), None, 'shape=plaintext')
            g.edge(c.name, key, 'style=dotted')

    walk(root, 0)
    return g.text()


def containment(rel: Relations, c, depth: int = 1, refs: bool = True,
                url: Callable = None) -> str:
    """What `c` holds (its own and inherited fields), `depth` steps out, by
    declared type."""
    g = _Graph("containment_%s" % c.name, rankdir="LR", url=url)
    kinds = (OWNS, OWNS_LIST, REFS, BACK) if refs else (OWNS, OWNS_LIST)
    seen = set()

    def walk(n, level):
        g.node(n.name, _class_label(rel, n), n, 'style="rounded,bold"' if n is c else "")
        if level >= depth or n.name in seen:
            return
        seen.add(n.name)
        for e in rel.edges(n, inherited=True):
            if e.kind not in kinds or not isinstance(e.target, AstClass):
                continue
            g.node(e.target.name, _class_label(rel, e.target), e.target)
            g.edge(n.name, e.target.name, "label=%s, %s" % (_q(_edge_label(e)), _EDGE_STYLE[e.kind]))
            if e.kind in (OWNS, OWNS_LIST):
                walk(e.target, level + 1)

    walk(c, 0)
    return g.text()


def neighbourhood(rel: Relations, c, url: Callable = None, max_children: int = 8,
                  max_owners: int = 8) -> str:
    """One step around `c`: its base and subclasses, what it holds, and the
    classes whose fields are declared as `c`."""
    g = _Graph("neighbourhood_%s" % c.name, rankdir="LR", url=url)
    g.node(c.name, _class_label(rel, c), c, 'style="rounded,bold"')

    sup = rel.superclass(c)
    if sup is not None:
        g.node(sup.name, sup.name, sup)
        g.edge(sup.name, c.name, "dir=back, arrowtail=empty")
    subs = rel.subclasses(c)
    for s in subs[:max_children]:
        g.node(s.name, _class_label(rel, s), s)
        g.edge(c.name, s.name, "dir=back, arrowtail=empty")
    if len(subs) > max_children:
        key = "%s.subs" % c.name
        g.node(key, "+%d more subclasses" % (len(subs) - max_children), None, "shape=plaintext")
        g.edge(c.name, key, "dir=back, arrowtail=empty, style=dotted")

    for e in rel.edges(c):
        if e.kind in _EDGE_STYLE and isinstance(e.target, AstClass):
            g.node(e.target.name, _class_label(rel, e.target), e.target)
            g.edge(c.name, e.target.name, "label=%s, %s" % (_q(_edge_label(e)), _EDGE_STYLE[e.kind]))

    direct, _ = rel.appears_in(c, kinds=(OWNS, OWNS_LIST, REFS))
    for e in direct[:max_owners]:
        g.node(e.cls.name, _class_label(rel, e.cls), e.cls)
        g.edge(e.cls.name, c.name, "label=%s, %s" % (_q(_edge_label(e)), _EDGE_STYLE[e.kind]))
    if len(direct) > max_owners:
        key = "%s.owners" % c.name
        g.node(key, "+%d more fields" % (len(direct) - max_owners), None, "shape=plaintext")
        g.edge(key, c.name, "style=dotted")
    return g.text()


def group_of(c) -> str:
    """A class's group: its YAML file's base name (`expr` for expr.yaml)."""
    if not c.srcfile:
        return "(model)"
    return os.path.splitext(os.path.basename(c.srcfile))[0]


def model_map(rel: Relations, url: Callable = None, labels: dict = None,
              refs: bool = False) -> str:
    """One node per group (YAML file); an edge where a class in one group
    owns (and with `refs`, references) a class in another, labelled with how
    many fields do. `url` here maps a group name to a link; `labels` a group
    name to a node label.

    Owning edges only, top to bottom, with parallel edges merged, by default:
    with references as well, pssparser's 18 groups have over 50 edges and the
    map stops being readable at page width."""
    g = _Graph("model_map", rankdir="TB")
    g.lines[1] = g.lines[1].replace("];", ", concentrate=true];")
    groups = sorted({group_of(c) for c in rel.ast.classes})
    counts = {}
    for c in rel.ast.classes:
        for e in rel.edges(c):
            kinds = (OWNS, OWNS_LIST, REFS) if refs else (OWNS, OWNS_LIST)
            if e.kind in kinds and isinstance(e.target, AstClass):
                a, b = group_of(c), group_of(e.target)
                if a != b:
                    k = (a, b, e.kind in (OWNS, OWNS_LIST))
                    counts[k] = counts.get(k, 0) + 1
    for grp in groups:
        n = sum(1 for c in rel.ast.classes if group_of(c) == grp)
        label = "%s\n%d class%s" % ((labels or {}).get(grp, grp), n, "" if n == 1 else "es")
        attrs = ["label=%s" % _q(label)]
        if url is not None and url(grp):
            attrs += ["URL=%s" % _q(url(grp)), 'target="_top"']
        g.lines.append("  %s [%s];" % (_q(grp), ", ".join(attrs)))
    for (a, b, owns), n in sorted(counts.items()):
        style = _EDGE_STYLE[OWNS] if owns else _EDGE_STYLE[REFS]
        g.edge(a, b, "label=%s, %s" % (_q(str(n)), style))
    return g.text()


def legend() -> str:
    """The edge conventions, drawn once."""
    g = _Graph("legend", rankdir="LR")
    rows = [
        ("Base", "Derived", "dir=back, arrowtail=empty", "inherits"),
        ("Owner", "Child", "label=\"field\", " + _EDGE_STYLE[OWNS], "owns one"),
        ("Owner2", "Children", "label=\"field[*]\", " + _EDGE_STYLE[OWNS_LIST], "owns many"),
        ("From", "To", "label=\"field\", " + _EDGE_STYLE[REFS], "refers to"),
        ("Child2", "Parent", "label=\"parent\", " + _EDGE_STYLE[BACK], "back-pointer"),
    ]
    for a, b, attrs, what in rows:
        g.node(a, a.rstrip("2"))
        g.node(b, b.rstrip("2"))
        g.edge(a, b, attrs)
        g.node(what, what, None, "shape=plaintext")
        g.edge(b, what, "style=invis")
    return g.text()
