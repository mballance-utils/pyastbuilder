'''
Sphinx support for astbuilder models: `extensions = ["astbuilder.sphinx"]`.

Documents a model from its YAML, at documentation-build time: each class
with its place in the inheritance and containment trees, its fields and what
they mean, where it can appear, and how every target API (C++, Python,
TypeScript, a rule language, ...) spells each field. Nothing is generated
into the source tree and nothing needs building first.

Configuration, in conf.py::

    astbuilder_models = {
        "pss": {
            "yaml": ["../ast/*.yaml"],               # globs, relative to conf.py
            "projections": [                          # columns of the projection table
                {"projection": "cpp", "namespace": "pssp::ast"},
                {"projection": "python", "module": "pssparser.ast"},
                "ts",
                "mypkg.docs:RuleProjection",          # a Projection subclass
            ],
            "groups": [("coretypes", "Scopes and core classes"), ...],
            "roots": ["GlobalScope", "RootSymbolScope"],
            "phases": [("parser", "Set when the source is parsed"),
                       ("linker", "Set when the linker resolves names")],
            "paths": True,      # show containment paths from the roots
            "doc_sections": True,       # use Attributes:/See Also: in class docs
            "doc_backticks": "literal", # read `x` in doc text as ``x``
        },
    }

A group is a YAML file's base name (`expr` for expr.yaml); `groups` orders
and titles them. The first phase is the default for a field with no
`set_by:`.

With `doc_sections` (the default), a class doc's Google-style
`Attributes:` section describes the fields that have no `doc:` of their
own, and its `See Also:` names become links (astbuilder.docstring). With
`doc_backticks: "literal"`, single backticks in doc text are code, as in
Markdown, rather than reST's default role.

Directives and roles are in the `astb` domain; see astbuilder.sphinx.directives.
Diagrams need `dot` (Graphviz). Without it the build warns once per diagram
and the text forms beside each diagram still render.
'''
import glob
import os

from ..ast import Ast
from ..linker import Linker
from ..parser import Parser
from ..projection import load_projection
from ..relations import Relations

__all__ = ["setup", "Model", "get_model"]


class Model(object):
    """One configured model: the parsed schema, its relationship graph, its
    projections, and its documentation settings."""

    def __init__(self, name, conf, confdir):
        self.name = name
        self.conf = conf
        patterns = conf.get("yaml") or []
        if isinstance(patterns, str):
            patterns = [patterns]
        self.files = []
        for p in patterns:
            matched = sorted(glob.glob(os.path.join(confdir, p)))
            if not matched:
                raise ValueError("astbuilder_models[%r]: no files match %r" % (name, p))
            self.files.extend(os.path.abspath(m) for m in matched)

        self.ast = Ast()
        for f in self.files:
            with open(f) as fp:
                Parser(self.ast, f).parse(fp)
        Linker().link(self.ast)

        self.rel = Relations(self.ast, roots=conf.get("roots") or ())
        self.doc_sections = bool(conf.get("doc_sections", True))
        self.doc_backticks = conf.get("doc_backticks")
        if self.doc_backticks not in (None, "literal"):
            raise ValueError("astbuilder_models[%r]: doc_backticks must be None or "
                             "'literal'" % name)
        self._parts = {}
        self.show_paths = bool(conf.get("paths", True))

        self.projections = []
        for spec in conf.get("projections") or []:
            if isinstance(spec, dict):
                opts = dict(spec)
                p = opts.pop("projection")
            else:
                p, opts = spec, {}
            self.projections.append(load_projection(p, self.ast, **opts))

        self.phases = [tuple(p) if not isinstance(p, str) else (p, "")
                       for p in (conf.get("phases") or [])]
        self.default_phase = self.phases[0][0] if self.phases else None

        titles = conf.get("groups") or []
        self.group_titles = {g: t for g, t in titles}
        present = sorted({self.group_of(c) for c in self.all_entities()})
        ordered = [g for g, _ in titles if g in present]
        self.groups = ordered + [g for g in present if g not in ordered]

    # -- entities -------------------------------------------------------------

    def all_entities(self):
        return (list(self.ast.classes) + list(self.ast.structs)
                + list(self.ast.enums) + list(self.ast.flags))

    @staticmethod
    def group_of(ent):
        f = getattr(ent, "srcfile", None)
        return os.path.splitext(os.path.basename(f))[0] if f else "(model)"

    def group_title(self, g):
        return self.group_titles.get(g, g)

    def in_group(self, g):
        """(classes, structs, enums, flags) of group `g`, each by name."""
        def pick(xs):
            return sorted((x for x in xs if self.group_of(x) == g), key=lambda x: x.name)
        return (pick(self.ast.classes), pick(self.ast.structs),
                pick(self.ast.enums), pick(self.ast.flags))

    def lookup(self, name):
        """The class, struct, enum or flags called `name`, or None."""
        for m in (self.ast.class_m, self.ast.struct_m, self.ast.enum_m, self.ast.flags_m):
            if name in m:
                return m[name]
        return None

    # -- doc text ---------------------------------------------------------------

    def prep(self, text):
        """Doc text as it is parsed: with the model's backtick convention."""
        if text and self.doc_backticks == "literal":
            from ..docstring import backticks_to_literal
            return backticks_to_literal(text)
        return text

    def doc_parts(self, ent):
        """`ent`'s doc split into body, attributes and See Also lines."""
        from ..docstring import DocParts, split
        key = (type(ent).__name__, ent.name)
        if key not in self._parts:
            doc = getattr(ent, "doc", None) or ""
            self._parts[key] = split(doc) if self.doc_sections else DocParts(doc)
        return self._parts[key]

    def field_doc(self, cls, field, described_by=None):
        """(text, entity whose doc it comes from) for `field`: its own
        `doc:`, else the Attributes entry of `described_by` (default: the
        declaring class), else (None, None)."""
        if field.doc and described_by is None:
            return field.doc, field
        owner = described_by if described_by is not None else cls
        text = self.doc_parts(owner).attributes.get(field.name)
        return (text, owner) if text else (None, None)

    def phase_of(self, cls, field):
        return self.rel.set_by(cls, field, default=self.default_phase)

    def phase_label(self, phase):
        for n, d in self.phases:
            if n == phase:
                return d
        return None


def get_model(app, name=None):
    """The Model called `name` (the first configured when None), loaded once
    per process."""
    models = app.config.astbuilder_models or {}
    if not models:
        raise ValueError("astbuilder_models is empty")
    if name is None:
        name = next(iter(models))
    if name not in models:
        raise ValueError("no astbuilder model %r (have: %s)" % (name, ", ".join(models)))
    cache = app.__dict__.setdefault("_astbuilder_models", {})
    if name not in cache:
        cache[name] = Model(name, models[name], app.confdir)
    return cache[name]


def model_report(model):
    """(warnings, notes) about a model's documentation, as text lines.

    Warnings are mistakes: a `set_by:` phase the configuration does not
    list. Notes are coverage: classes and fields with no `doc:`, classes no
    root contains, raw-pointer fields with no `rel:`."""
    from ..type_list import TypeList
    from ..type_pointer import TypePointer, PointerKind
    warnings, notes = [], []
    known = {p for p, _ in model.phases}
    ast = model.ast
    if known:
        for c in ast.classes:
            for ent, what in [(c, c.name)] + [(d, "%s.%s" % (c.name, d.name)) for d in c.data]:
                ph = getattr(ent, "set_by", None)
                if ph is not None and ph not in known:
                    warnings.append("%s:%d: %s: set_by: %r is not a configured phase (%s)" % (
                        ent.srcfile, ent.srcline, what, ph, ", ".join(sorted(known))))
    fields = [(c, d) for c in ast.classes for d in c.data]
    no_cdoc = [c for c in ast.classes if not c.doc]
    # A field is documented by its own doc: or, with doc_sections, by its
    # class's Attributes: entry -- whichever the pages show.
    no_fdoc = [(c, d) for c, d in fields if not model.field_doc(c, d)[0]]
    notes.append("%d of %d classes and %d of %d fields have no description" % (
        len(no_cdoc), len(ast.classes), len(no_fdoc), len(fields)))
    valued = list(ast.enums) + list(ast.flags)
    no_edoc = [e for e in valued if not e.doc]
    vals = [(e, v[0] if isinstance(v, tuple) else v) for e in valued for v in e.values]
    no_vdoc = [(e, v) for e, v in vals if not e.value_docs.get(v)]
    notes.append("%d of %d enums and flags and %d of %d values have no description" % (
        len(no_edoc), len(valued), len(no_vdoc), len(vals)))
    unreach = model.rel.unreachable()
    if unreach:
        notes.append("%d classes no root contains: %s" % (
            len(unreach), ", ".join(c.name for c in unreach)))

    def raw(t):
        t = t.t if isinstance(t, TypeList) else t
        return isinstance(t, TypePointer) and t.pt == PointerKind.Raw
    no_rel = [(c, d) for c, d in fields if raw(d.t) and d.rel is None]
    if no_rel:
        notes.append("%d P<T> fields have no rel: (shown as references): %s" % (
            len(no_rel), ", ".join("%s.%s" % (c.name, d.name) for c, d in no_rel)))
    return warnings, notes


def _check_consistency(app, env):
    from sphinx.util import logging
    logger = logging.getLogger(__name__)
    for name, model in sorted(app.__dict__.get("_astbuilder_models", {}).items()):
        warnings, notes = model_report(model)
        for w in warnings:
            logger.warning("astbuilder model %s: %s", name, w)
        for n in notes:
            logger.info("astbuilder model %s: %s", name, n)


def _builder_inited(app):
    # The stylesheet that keeps wide tables within the page (HTML only).
    if app.builder.format == "html":
        static = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        app.config.html_static_path.append(static)
        app.add_css_file("astb.css")


def _config_inited(app, config):
    # Diagram nodes are links only in SVG. Prefer it unless the project chose.
    if "graphviz_output_format" not in config._raw_config:
        config.graphviz_output_format = "svg"


def setup(app):
    from . import directives, domain

    app.setup_extension("sphinx.ext.graphviz")
    app.add_config_value("astbuilder_models", {}, "env")
    app.connect("config-inited", _config_inited)
    app.connect("env-check-consistency", _check_consistency)
    app.connect("builder-inited", _builder_inited)
    domain.setup(app)
    directives.setup(app)
    from ..__version__ import _pkg_version
    return {
        "version": _pkg_version,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "env_version": 1,
    }
