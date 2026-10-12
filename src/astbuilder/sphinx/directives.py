'''
Directives of the `astb` domain.

Entries:

    .. astb:model:: [model]          every entity of a model, or of one group
       :group: expr                  (one YAML file); records the group's page
    .. astb:class:: ExprBin          one class
    .. astb:struct:: / astb:enum:: / astb:flags::

Relationships:

    .. astb:model-map:: [model]      one node per group (the landing page)
    .. astb:inheritance-tree:: Expr  a nested list below a class  (:depth:)
    .. astb:inheritance-diagram:: Expr                 (:depth:, :max-children:)
    .. astb:containment-diagram:: Action               (:depth:, :no-refs:)
    .. astb:neighbourhood:: ExprBin
    .. astb:relations-table:: ExprBin
    .. astb:projection-table:: ExprBin
    .. astb:legend::

Every directive takes `:model:` (default: the first configured). Each
diagram directive also emits the view as text (a nested list or a table)
unless given `:no-text:`, because a diagram cannot be searched or read by a
screen reader. A class entry's neighbourhood diagram needs no separate text:
the entry's own sections say the same. Diagrams are resolved to
Graphviz nodes once every page is read, so their nodes can link to entries
on any page.

Class-entry options (also accepted by astb:model): `:no-diagram:`,
`:no-projections:`, `:no-appears-in:`, `:no-paths:`.
'''
from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective, switch_source_input

from .. import diagrams
from ..ast_class import AstClass
from ..ast_enum import AstEnum
from ..ast_flags import AstFlags
from ..ast_struct import AstStruct
from ..relations import BACK, OWNS, OWNS_LIST, REFS, VALUE
from . import get_model
from .domain import anchor, current_docname, xref

logger = logging.getLogger(__name__)

_KIND_TEXT = {
    OWNS: "owns",
    OWNS_LIST: "owns a list of",
    REFS: "refers to",
    BACK: "back-pointer to",
    VALUE: "value",
}

#: How many entries an "appears in" group lists before "and N more".
_APPEARS_LIMIT = 12
#: How many subclasses a class entry lists before "and N more".
_SUBCLASS_LIMIT = 40


# ==========================================================================
# Nodes
# ==========================================================================

class astb_diagram(nodes.General, nodes.Element):
    """A diagram to be drawn once every page has been read; replaced by a
    Graphviz node in doctree-resolved. Attributes: view, model, target,
    options."""


def _resolve_diagrams(app, doctree, docname):
    from sphinx.ext.graphviz import graphviz
    domain = app.env.get_domain("astb")
    for node in list(doctree.findall(astb_diagram)):
        model = get_model(app, node["model"])
        rel = model.rel
        opts = node["options"]

        def url(c, _docname=docname):
            return domain.uri(app.builder, _docname, c.name)

        view = node["view"]
        tgt = model.lookup(node["target"]) if node["target"] else None
        if view == "inheritance":
            code = diagrams.inheritance(rel, tgt, depth=opts.get("depth"), url=url,
                                        max_children=opts.get("max_children") or 0)
        elif view == "containment":
            code = diagrams.containment(rel, tgt, depth=opts.get("depth") or 1,
                                        refs=not opts.get("no_refs"), url=url)
        elif view == "neighbourhood":
            code = diagrams.neighbourhood(rel, tgt, url=url)
        elif view == "map":
            code = diagrams.model_map(
                rel, url=lambda g: domain.group_uri(app.builder, docname, model.name, g),
                refs=bool(opts.get("refs")))
        else:
            code = diagrams.legend()
        g = graphviz()
        g["code"] = code
        g["options"] = {"docname": docname}
        g["alt"] = node.get("alt", view)
        g["classes"] = ["astb-diagram"]
        node.replace_self(g)


# ==========================================================================
# Helpers
# ==========================================================================

def _table(headers, rows, widths=None, classes=()):
    """A table of `rows`, each a list of cells; a cell is a string, a node,
    or a list of nodes."""
    table = nodes.table(classes=["astb-table"] + list(classes))
    tgroup = nodes.tgroup(cols=len(headers))
    table += tgroup
    for w in widths or [1] * len(headers):
        tgroup += nodes.colspec(colwidth=w)

    def cell(v):
        entry = nodes.entry()
        if isinstance(v, str):
            entry += nodes.paragraph(v, v)
        elif isinstance(v, (nodes.Inline, nodes.Text)):
            entry += nodes.paragraph("", "", v)
        elif isinstance(v, nodes.Node):
            entry += v
        else:
            p = nodes.paragraph()
            for x in v:
                p += x
            entry += p
        return entry

    thead = nodes.thead()
    row = nodes.row()
    for h in headers:
        row += cell(h)
    thead += row
    tgroup += thead
    tbody = nodes.tbody()
    for r in rows:
        row = nodes.row()
        for v in r:
            row += cell(v)
        tbody += row
    tgroup += tbody
    return table


def _joined(items, sep=", "):
    """Nodes joined by `sep` text."""
    ret = []
    for i, x in enumerate(items):
        if i:
            ret.append(nodes.Text(sep))
        ret.append(x)
    return ret


def _para(*parts):
    p = nodes.paragraph()
    for x in parts:
        if isinstance(x, str):
            p += nodes.Text(x)
        elif isinstance(x, list):
            for y in x:
                p += y
        else:
            p += x
    return p


def _strong(text):
    return nodes.strong(text, text)


def _type_ref(ent):
    if isinstance(ent, AstClass):
        return xref("class", ent.name)
    if isinstance(ent, AstStruct):
        return xref("struct", ent.name)
    if isinstance(ent, AstFlags):
        return xref("flags", ent.name)
    if isinstance(ent, AstEnum):
        return xref("enum", ent.name)
    return nodes.literal(str(ent), str(ent))


def _field_ref(cls, field):
    return xref("field", "%s.%s" % (cls.name, field.name), text=field.name)


def _yaml_type(t):
    """The field's type as written in the YAML."""
    from ..type_list import TypeList
    from ..type_map import TypeMap
    from ..type_pointer import TypePointer, PointerKind
    from ..type_scalar import TypeScalar
    from ..type_userdef import TypeUserDef
    if isinstance(t, TypePointer):
        p = {PointerKind.Unique: "UP", PointerKind.Shared: "SP", PointerKind.Raw: "P"}[t.pt]
        return "%s<%s>" % (p, _yaml_type(t.t))
    if isinstance(t, TypeList):
        return "list<%s>" % _yaml_type(t.t)
    if isinstance(t, TypeMap):
        return "map<%s,%s>" % (_yaml_type(t.kt), _yaml_type(t.vt))
    if isinstance(t, TypeUserDef):
        return t.name
    if isinstance(t, TypeScalar):
        return {
            "String": "string", "Bool": "bool", "Float32": "float", "Float64": "double",
        }.get(t.t.name, t.t.name.lower() + "_t")
    return str(t)


def _type_cell(edge):
    """`UP<Expr>` with the class name linked."""
    text = _yaml_type(edge.field.t)
    if edge.target is None:
        return [nodes.literal(text, text)]
    name = edge.target.name
    i = text.find(name)
    ret = []
    if i > 0:
        ret.append(nodes.literal(text[:i], text[:i]))
    ret.append(_type_ref(edge.target))
    if i + len(name) < len(text):
        rest = text[i + len(name):]
        ret.append(nodes.literal(rest, rest))
    return ret


# ==========================================================================
# Base directive
# ==========================================================================

class _AstbDirective(SphinxDirective):
    has_content = False
    optional_arguments = 1
    final_argument_whitespace = False
    option_spec = {"model": directives.unchanged}

    def model(self):
        m = get_model(self.env.app, self.options.get("model"))
        self._model = m
        for f in m.files:
            self.env.note_dependency(f)
        return m

    def target_entity(self, model, kinds=None):
        if not self.arguments:
            raise self.error("%s needs a name" % self.name)
        ent = model.lookup(self.arguments[0])
        if ent is None or (kinds and not isinstance(ent, kinds)):
            raise self.error("%s: no %s named %r in model %s" % (
                self.name, "/".join(k.__name__[3:].lower() for k in (kinds or ())) or "entity",
                self.arguments[0], model.name))
        return ent

    def domain(self):
        return self.env.get_domain("astb")

    def diagram(self, model, view, target=None, alt=None, **opts):
        n = astb_diagram()
        n["model"] = model.name
        n["view"] = view
        n["target"] = target.name if target is not None else None
        n["options"] = opts
        n["alt"] = alt or view
        return n

    def parse_doc(self, text, ent, line=None):
        """`doc:` text as reST, with warnings pointing at the YAML: at `line`,
        else where `ent`'s doc starts, else where `ent` is declared."""
        if not text:
            return []
        text = self._model.prep(text)
        src = getattr(ent, "srcfile", None) or "<model>"
        if line is None or line < 1:
            line = getattr(ent, "docline", -1)
        if line < 1:
            line = getattr(ent, "srcline", -1)
        # StringList items are 0-based line offsets.
        line = max(line - 1, 0)
        lines = text.rstrip("\n").split("\n")
        content = StringList(lines, items=[(src, line + i) for i in range(len(lines))])
        holder = nodes.container()
        with switch_source_input(self.state, content):
            self.state.nested_parse(content, 0, holder)
        return list(holder.children)

    # -- entries ----------------------------------------------------------

    def _desc(self, objtype, name, annotation):
        desc = addnodes.desc(domain="astb", objtype=objtype, desctype=objtype, noindex=False)
        node_id = anchor(objtype, name)
        sig = addnodes.desc_signature("", "", ids=[node_id])
        sig += addnodes.desc_annotation(annotation + " ", annotation + " ")
        sig += addnodes.desc_name(name, name)
        desc += sig
        self.domain().note_object(name, objtype, node_id, location=(current_docname(self.env), self.lineno))
        index = addnodes.index(entries=[("single", "%s (AST %s)" % (name, objtype), node_id, "", None)])
        content = addnodes.desc_content()
        desc += content
        return [index, desc], sig, content

    def render_class(self, model, c):
        rel = model.rel
        out, sig, content = self._desc("class", c.name, "class")
        sup = rel.superclass(c)
        if sup is not None:
            sig += addnodes.desc_annotation(" : ", " : ")
            sig += xref("class", sup.name)

        # Where it sits
        info = []
        anc = rel.ancestors(c)
        if anc:
            crumbs = [xref("class", a.name) for a in reversed(anc)] + [nodes.literal(c.name, c.name)]
            info.append(_para(_strong("Inherits: "), _joined(crumbs, " › ")))
        subs = rel.subclasses(c)
        if subs:
            shown = subs[:_SUBCLASS_LIMIT]
            parts = _joined([xref("class", s.name) for s in shown])
            if len(subs) > len(shown):
                parts.append(nodes.Text(", and %d more" % (len(subs) - len(shown))))
            n = len(rel.descendants(c))
            more = " (%d in all)" % n if n > len(subs) else ""
            info.append(_para(_strong("Subclasses: "), parts, more))
        phase = getattr(c, "set_by", None)
        where = "Defined in %s" % model.group_of(c) + ".yaml"
        if c.srcline > 0:
            where += ", line %d" % c.srcline
        if phase:
            label = model.phase_label(phase)
            where += "; set by %s" % phase + (" (%s)" % label if label else "")
        info.append(_para(nodes.emphasis(where, where)))
        content.extend(info)

        parts = model.doc_parts(c)
        content.extend(self.parse_doc(parts.body, c))
        if parts.see_also:
            content.append(self.see_also(model, parts.see_also))

        if "no-diagram" not in self.options:
            content += self.diagram(model, "neighbourhood", c, alt="%s and its neighbours" % c.name)

        content.extend(self.fields_section(model, c))
        if "no-appears-in" not in self.options:
            content.extend(self.appears_in_section(model, c))
        if model.show_paths and "no-paths" not in self.options:
            content.extend(self.paths_section(model, c))
        if model.projections and "no-projections" not in self.options:
            content.extend(self.projection_section(model, c))
        return out

    def see_also(self, model, lines):
        """`See also:` with each line's names linked, or the line as text
        when it is prose."""
        from ..docstring import names
        parts = [_strong("See also: ")]
        for i, line in enumerate(lines):
            if i:
                parts.append(nodes.Text("; "))
            toks = names(line)
            if not toks:
                parts.append(nodes.Text(line))
                continue
            refs = []
            for t in toks:
                if "." in t:
                    refs.append(xref("field", t))
                else:
                    ent = model.lookup(t)
                    refs.append(_type_ref(ent) if ent is not None else nodes.literal(t, t))
            parts.extend(_joined(refs))
        return _para(*parts)

    def fields_section(self, model, c):
        rel = model.rel
        ret = []
        rows = []
        for e in rel.edges(c):
            d = e.field
            name_p = nodes.paragraph("", "", ids=[anchor("field", "%s.%s" % (c.name, d.name))])
            name_p += nodes.literal(d.name, d.name)
            self.domain().note_object("%s.%s" % (c.name, d.name), "field",
                                      anchor("field", "%s.%s" % (c.name, d.name)))
            relation = _KIND_TEXT[e.kind] if e.target is not None or e.kind != VALUE else "value"
            notes = []
            phase = model.phase_of(c, d)
            if phase and phase != model.default_phase:
                notes.append("set by %s" % phase)
            if notes:
                relation += " (%s)" % ", ".join(notes)
            text, src = model.field_doc(c, d)
            desc = self.parse_doc(text, src) if text else [nodes.paragraph("", "")]
            desc_cell = nodes.container()
            desc_cell.extend(desc)
            rows.append([name_p, _type_cell(e), relation, desc_cell])
        if rows:
            ret.append(nodes.rubric("Fields", "Fields"))
            ret.append(_table(["Field", "Type", "Relation", "Description"], rows, [16, 22, 16, 46]))
        inherited = []
        described = []
        for a in rel.ancestors(c):
            if a.data:
                inherited.append(_para("From ", xref("class", a.name), ": ",
                                       _joined([_field_ref(a, d) for d in a.data])))
                for d in a.data:
                    # This class's own description of an inherited field
                    # (`name: The covergroup's name`).
                    text, src = model.field_doc(a, d, described_by=c)
                    if text:
                        described.append([_field_ref(a, d)] + self._inline_doc(text, src))
        if inherited:
            ret.append(nodes.rubric("Inherited fields", "Inherited fields"))
            ret.extend(inherited)
            if described:
                items = nodes.bullet_list()
                for parts in described:
                    items += nodes.list_item("", _para(parts[0], nodes.Text(": "), *parts[1:]))
                ret.append(_para("As described for ", nodes.literal(c.name, c.name), ":"))
                ret.append(items)
        return ret

    def _inline_doc(self, text, ent):
        """A one-paragraph doc's inline nodes (for use inside a sentence);
        falls back to its plain text when it is more than one paragraph."""
        parsed = self.parse_doc(text, ent)
        if len(parsed) == 1 and isinstance(parsed[0], nodes.paragraph):
            return list(parsed[0].children)
        return [nodes.Text(" ".join(text.split()))]

    def appears_in_section(self, model, c):
        direct, via = model.rel.appears_in(c)
        if not direct and not via:
            return []
        ret = [nodes.rubric("Appears in", "Appears in")]
        items = nodes.bullet_list()

        def edge_list(es):
            shown = es[:_APPEARS_LIMIT]
            parts = _joined([xref("field", e.label) for e in shown])
            if len(es) > len(shown):
                parts.append(nodes.Text(", and %d more" % (len(es) - len(shown))))
            return parts

        if direct:
            items += nodes.list_item("", _para(_strong("As itself: "), edge_list(direct)))
        for a, es in via:
            items += nodes.list_item("", _para(
                _strong("Through "), xref("class", a.name), _strong(": "), edge_list(es)))
        ret.append(items)
        return ret

    def paths_section(self, model, c):
        paths = model.rel.containment_paths(c)
        if not paths:
            return []
        ret = [nodes.rubric("Containment", "Containment")]
        items = nodes.bullet_list()
        for root, path in paths.items():
            if not path:
                items += nodes.list_item("", _para(xref("class", root), " is a root"))
                continue
            parts = [xref("class", root)]
            for e, reached in path:
                parts.append(nodes.Text(" → "))
                parts.append(xref("field", e.label))
                if e.target is not reached:
                    parts.append(nodes.Text(" (as "))
                    parts.append(xref("class", e.target.name))
                    parts.append(nodes.Text(")"))
            items += nodes.list_item("", _para(parts))
        ret.append(items)
        return ret

    def projection_section(self, model, c, own_only=True):
        projs = model.projections
        if own_only and not c.data:
            return []
        rows = []
        for d in c.data:
            row = [nodes.literal(d.name, d.name)]
            for p in projs:
                acc = p.accessors(c, d)
                if not acc:
                    why = p.hidden(c, d) or "not exposed"
                    row.append(nodes.emphasis("— " + why, "— " + why))
                    continue
                cell = nodes.line_block()
                for a in acc:
                    line = nodes.line()
                    line += nodes.literal(a.text, a.text)
                    if a.type and a.role in ("get", "view", "list", "at"):
                        line += nodes.Text(" → %s" % a.type)
                    cell += line
                row.append(cell)
            rows.append(row)
        heads = [nodes.paragraph("", "Field")]
        for p in projs:
            cn = p.class_name(c)
            heads.append(_para(p.label, nodes.Text(" "), nodes.literal(cn, cn)))
        return [nodes.rubric("In each API", "In each API"),
                _table(heads, rows, [14] + [86 // max(len(projs), 1)] * len(projs),
                       classes=["astb-projections"])]

    def render_values(self, model, e, objtype):
        out, sig, content = self._desc(objtype, e.name, objtype)
        where = "Defined in %s.yaml" % model.group_of(e)
        if e.srcline > 0:
            where += ", line %d" % e.srcline
        content += _para(nodes.emphasis(where, where))
        self._doc_body(model, e, content)
        rows = []
        values = [v[0] if isinstance(v, tuple) else v for v in e.values]
        for i, v in enumerate(values):
            name = "%s.%s" % (e.name, v)
            p = nodes.paragraph("", "", ids=[anchor("enumvalue", name)])
            p += nodes.literal(v, v)
            self.domain().note_object(name, "enumvalue", anchor("enumvalue", name))
            num = str(1 << i) if objtype == "flags" else str(i)
            doc = e.value_docs.get(v)
            dcell = nodes.container()
            if doc:
                dcell.extend(self.parse_doc(doc, e, e.value_doclines.get(v)))
            else:
                dcell += nodes.paragraph("", "")
            rows.append([p, num, dcell])
        content += _table(["Value", "Number" if objtype == "enum" else "Bit value", "Description"],
                          rows, [30, 12, 58])
        return out

    def _doc_body(self, model, ent, content):
        """`ent`'s doc without its Attributes: section (shown in the
        fields table), then its See Also: line."""
        parts = model.doc_parts(ent)
        content.extend(self.parse_doc(parts.body, ent))
        if parts.see_also:
            content.append(self.see_also(model, parts.see_also))

    def render_struct(self, model, s):
        out, sig, content = self._desc("struct", s.name, "struct")
        where = "Defined in %s.yaml" % model.group_of(s)
        if s.srcline > 0:
            where += ", line %d" % s.srcline
        content += _para(nodes.emphasis(where, where))
        self._doc_body(model, s, content)
        rows = []
        for e in model.rel.edges(s):
            name = "%s.%s" % (s.name, e.field.name)
            p = nodes.paragraph("", "", ids=[anchor("field", name)])
            p += nodes.literal(e.field.name, e.field.name)
            self.domain().note_object(name, "field", anchor("field", name))
            dcell = nodes.container()
            text, src = model.field_doc(s, e.field)
            dcell.extend((self.parse_doc(text, src) if text else None)
                         or [nodes.paragraph("", "")])
            rows.append([p, _type_cell(e), dcell])
        if rows:
            content += _table(["Field", "Type", "Description"], rows, [20, 25, 55])
        return out

    def render_entity(self, model, ent):
        if isinstance(ent, AstClass):
            return self.render_class(model, ent)
        if isinstance(ent, AstStruct):
            return self.render_struct(model, ent)
        if isinstance(ent, AstFlags):
            return self.render_values(model, ent, "flags")
        return self.render_values(model, ent, "enum")


_ENTRY_FLAGS = {
    "no-diagram": directives.flag,
    "no-projections": directives.flag,
    "no-appears-in": directives.flag,
    "no-paths": directives.flag,
}


# ==========================================================================
# Entry directives
# ==========================================================================

class ClassDirective(_AstbDirective):
    required_arguments = 1
    optional_arguments = 0
    option_spec = dict(_AstbDirective.option_spec, **_ENTRY_FLAGS)

    def run(self):
        model = self.model()
        return self.render_class(model, self.target_entity(model, (AstClass,)))


class StructDirective(_AstbDirective):
    required_arguments = 1
    optional_arguments = 0

    def run(self):
        model = self.model()
        return self.render_struct(model, self.target_entity(model, (AstStruct,)))


class EnumDirective(_AstbDirective):
    required_arguments = 1
    optional_arguments = 0

    def run(self):
        model = self.model()
        ent = self.target_entity(model, (AstEnum, AstFlags))
        return self.render_values(model, ent, "flags" if isinstance(ent, AstFlags) else "enum")


class ModelDirective(_AstbDirective):
    """Every entity of a model, or of one group, in the order: enums,
    flags, structs, classes (classes in inheritance order within the group,
    a base before its subclasses)."""
    option_spec = dict(_AstbDirective.option_spec, group=directives.unchanged, **_ENTRY_FLAGS)

    def run(self):
        if self.arguments:
            self.options.setdefault("model", self.arguments[0])
        model = self.model()
        groups = [self.options["group"]] if "group" in self.options else model.groups
        ret = []
        for g in groups:
            if g not in model.groups:
                raise self.error("model %s has no group %r (groups: %s)" % (
                    model.name, g, ", ".join(model.groups)))
            gid = "astb-group-%s-%s" % (model.name, g)
            ret.append(nodes.target("", "", ids=[gid]))
            self.domain().note_group(model.name, g, gid)
            classes, structs, enums, flags = model.in_group(g)
            for e in enums:
                ret.extend(self.render_values(model, e, "enum"))
            for f in flags:
                ret.extend(self.render_values(model, f, "flags"))
            for s in structs:
                ret.extend(self.render_struct(model, s))
            for c in _inheritance_order(model, classes):
                ret.extend(self.render_class(model, c))
        return ret


def _inheritance_order(model, classes):
    """`classes` with each base before its subclasses, siblings by name."""
    names = {c.name for c in classes}
    roots = [c for c in classes
             if model.rel.superclass(c) is None or model.rel.superclass(c).name not in names]
    ret = []

    def walk(c):
        ret.append(c)
        for s in model.rel.subclasses(c):
            if s.name in names:
                walk(s)

    for r in sorted(roots, key=lambda c: c.name):
        walk(r)
    return ret


# ==========================================================================
# Relationship directives
# ==========================================================================

class ModelMapDirective(_AstbDirective):
    """The landing view: one node per group, and a list of the groups (each
    linked to the page that renders it) with their counts. `:refs:` adds
    reference edges to the map."""
    option_spec = dict(_AstbDirective.option_spec, refs=directives.flag)

    def run(self):
        if self.arguments:
            self.options.setdefault("model", self.arguments[0])
        model = self.model()
        ret = [self.diagram(model, "map", alt="Map of the %s model" % model.name,
                            refs="refs" in self.options)]
        items = nodes.bullet_list()
        for g in model.groups:
            classes, structs, enums, flags = model.in_group(g)
            title = model.group_title(g)
            counts = []
            for n, what in ((len(classes), "class"), (len(structs), "struct"),
                            (len(enums), "enum"), (len(flags), "flags")):
                if n:
                    counts.append("%d %s%s" % (n, what, "" if n == 1 or what == "flags" else
                                               ("es" if what == "class" else "s")))
            ref = addnodes.pending_xref("", refdomain="astb", reftype="group",
                                        reftarget="%s:%s" % (model.name, g), refwarn=False)
            ref += nodes.Text(title)
            strong = nodes.strong()
            strong += ref
            p = _para(strong, " (%s.yaml): %s" % (g, ", ".join(counts)))
            items += nodes.list_item("", p)
        ret.append(items)
        return ret


_NO_TEXT = {"no-text": directives.flag}


def _held_by(e):
    return "held by" if e.kind in (OWNS, OWNS_LIST) else "referenced by"


class _TextForms(object):
    """The text forms of the relationship views, shared by the diagram
    directives (which emit them beside the diagram unless `:no-text:`) and
    the text-only directives."""

    def inheritance_tree(self, model, root, depth=None):
        rel = model.rel

        def walk(c, level):
            item = nodes.list_item()
            p = _para(xref("class", c.name))
            subs = rel.subclasses(c)
            if depth is not None and level >= depth and subs:
                p += nodes.Text(" (+%d below)" % len(rel.descendants(c)))
            item += p
            if subs and (depth is None or level < depth):
                bl = nodes.bullet_list()
                for s in subs:
                    bl += walk(s, level + 1)
                item += bl
            return item

        top = nodes.bullet_list(classes=["astb-tree"])
        top += walk(root, 0)
        return top

    def relations_table(self, model, c):
        rel = model.rel
        rows = []
        for e in rel.edges(c, inherited=True):
            if e.target is None or e.kind == VALUE:
                continue
            rows.append([xref("field", e.label), _KIND_TEXT[e.kind], _type_ref(e.target)])
        direct, via = rel.appears_in(c)
        for e in direct:
            rows.append([xref("field", e.label), _held_by(e), xref("class", e.cls.name)])
        for a, es in via:
            for e in es:
                rows.append([xref("field", e.label), _held_by(e) + " (as %s)" % a.name,
                             xref("class", e.cls.name)])
        if not rows:
            return _para("%s has no relationships." % c.name)
        return _table(["Field", "Relationship", "Class"], rows, [40, 30, 30])

    def containment_table(self, model, c, depth=1, refs=True):
        """The edges containment() draws, one row each."""
        rel = model.rel
        kinds = (OWNS, OWNS_LIST, REFS, BACK) if refs else (OWNS, OWNS_LIST)
        rows, seen = [], set()

        def walk(n, level):
            if level >= depth or n.name in seen:
                return
            seen.add(n.name)
            for e in rel.edges(n, inherited=True):
                if e.kind in kinds and isinstance(e.target, AstClass):
                    rows.append([xref("class", n.name), xref("field", e.label),
                                 _KIND_TEXT[e.kind], _type_ref(e.target)])
                    if e.kind in (OWNS, OWNS_LIST):
                        walk(e.target, level + 1)

        walk(c, 0)
        if not rows:
            return _para("%s holds no other nodes." % c.name)
        return _table(["Class", "Field", "Relationship", "Holds"], rows, [25, 30, 20, 25])

    def legend_list(self):
        items = nodes.bullet_list()
        for what, how in (
                ("inherits", "a hollow triangle at the base class"),
                ("owns one", "a solid line with a filled arrow, labelled with the field"),
                ("owns many", "the same, with the field labelled name[*] (name{key} for a map)"),
                ("refers to", "a dashed line with an open arrow"),
                ("back-pointer", "a dotted grey line with an open arrow"),
                ("Name (+N)", "a class with N classes below it; an edge to it means it or any of them")):
            items += nodes.list_item("", _para(_strong(what + ": "), how))
        return items


class InheritanceTreeDirective(_AstbDirective, _TextForms):
    required_arguments = 1
    optional_arguments = 0
    option_spec = dict(_AstbDirective.option_spec, depth=directives.nonnegative_int)

    def run(self):
        model = self.model()
        root = self.target_entity(model, (AstClass,))
        return [self.inheritance_tree(model, root, self.options.get("depth"))]


class InheritanceDiagramDirective(_AstbDirective, _TextForms):
    required_arguments = 1
    optional_arguments = 0
    option_spec = dict(_AstbDirective.option_spec, depth=directives.nonnegative_int,
                       **{"max-children": directives.nonnegative_int}, **_NO_TEXT)

    def run(self):
        model = self.model()
        root = self.target_entity(model, (AstClass,))
        depth = self.options.get("depth")
        ret = [self.diagram(model, "inheritance", root, alt="Classes derived from %s" % root.name,
                            depth=depth, max_children=self.options.get("max-children"))]
        if "no-text" not in self.options:
            ret.append(self.inheritance_tree(model, root, depth))
        return ret


class ContainmentDiagramDirective(_AstbDirective, _TextForms):
    required_arguments = 1
    optional_arguments = 0
    option_spec = dict(_AstbDirective.option_spec, depth=directives.positive_int,
                       **{"no-refs": directives.flag}, **_NO_TEXT)

    def run(self):
        model = self.model()
        c = self.target_entity(model, (AstClass,))
        depth = self.options.get("depth") or 1
        refs = "no-refs" not in self.options
        ret = [self.diagram(model, "containment", c, alt="What %s holds" % c.name,
                            depth=depth, no_refs=not refs)]
        if "no-text" not in self.options:
            ret.append(self.containment_table(model, c, depth, refs))
        return ret


class NeighbourhoodDirective(_AstbDirective, _TextForms):
    required_arguments = 1
    optional_arguments = 0
    option_spec = dict(_AstbDirective.option_spec, **_NO_TEXT)

    def run(self):
        model = self.model()
        c = self.target_entity(model, (AstClass,))
        ret = [self.diagram(model, "neighbourhood", c, alt="%s and its neighbours" % c.name)]
        if "no-text" not in self.options:
            ret.append(self.relations_table(model, c))
        return ret


class RelationsTableDirective(_AstbDirective, _TextForms):
    """A class's relationships as a table: what it holds and refers to (own
    and inherited fields), and what holds it."""
    required_arguments = 1
    optional_arguments = 0

    def run(self):
        model = self.model()
        return [self.relations_table(model, self.target_entity(model, (AstClass,)))]


class ProjectionTableDirective(_AstbDirective):
    required_arguments = 1
    optional_arguments = 0

    def run(self):
        model = self.model()
        c = self.target_entity(model, (AstClass,))
        return self.projection_section(model, c)[1:] or [_para("%s has no fields." % c.name)]


class LegendDirective(_AstbDirective, _TextForms):
    optional_arguments = 1
    option_spec = dict(_AstbDirective.option_spec, **_NO_TEXT)

    def run(self):
        if self.arguments:
            self.options.setdefault("model", self.arguments[0])
        model = self.model()
        ret = [self.diagram(model, "legend", alt="Diagram legend")]
        if "no-text" not in self.options:
            ret.append(self.legend_list())
        return ret


def setup(app):
    app.add_node(astb_diagram)
    app.add_directive_to_domain("astb", "model", ModelDirective)
    app.add_directive_to_domain("astb", "class", ClassDirective)
    app.add_directive_to_domain("astb", "struct", StructDirective)
    app.add_directive_to_domain("astb", "enum", EnumDirective)
    app.add_directive_to_domain("astb", "flags", EnumDirective)
    app.add_directive_to_domain("astb", "model-map", ModelMapDirective)
    app.add_directive_to_domain("astb", "inheritance-tree", InheritanceTreeDirective)
    app.add_directive_to_domain("astb", "inheritance-diagram", InheritanceDiagramDirective)
    app.add_directive_to_domain("astb", "containment-diagram", ContainmentDiagramDirective)
    app.add_directive_to_domain("astb", "neighbourhood", NeighbourhoodDirective)
    app.add_directive_to_domain("astb", "relations-table", RelationsTableDirective)
    app.add_directive_to_domain("astb", "projection-table", ProjectionTableDirective)
    app.add_directive_to_domain("astb", "legend", LegendDirective)
    app.connect("doctree-resolved", _resolve_diagrams)
