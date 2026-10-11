'''
The `astb` domain: object types, roles and cross-reference resolution.

Objects are keyed by name: `ExprBin` (class), `ExprBin.lhs` (field),
`ExprBinOp` (enum), `ExprBinOp.BinOp_Add` (enum value). A role that does not
resolve is a warning, so a `-W` build fails when hand-written prose names
something the model no longer has. Links the extension generates itself
(a field's type, a subclass) degrade to plain text when the target is not
documented anywhere in the project.

Groups (one per YAML file) are recorded too, so the model map can link each
group to the page that renders it.
'''
from docutils import nodes
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.nodes import make_refnode

logger = logging.getLogger(__name__)

OBJTYPES = ("class", "struct", "enum", "flags", "field", "enumvalue")


def current_docname(env):
    """The document being read (`env.docname` before Sphinx 8.2)."""
    cur = getattr(env, "current_document", None)
    return cur.docname if cur is not None else env.docname


def anchor(objtype, name):
    """The HTML id of an object: `astb-class-ExprBin`, `astb-field-ExprBin-lhs`."""
    return "astb-%s-%s" % (objtype, name.replace(".", "-"))


class AstbDomain(Domain):
    name = "astb"
    label = "AST model"
    object_types = {
        "class": ObjType("class", "class", "type"),
        "struct": ObjType("struct", "struct", "type"),
        "enum": ObjType("enum", "enum", "type"),
        "flags": ObjType("flags", "flags", "enum", "type"),
        "field": ObjType("field", "field"),
        "enumvalue": ObjType("enum value", "enumvalue"),
    }
    roles = {
        "class": XRefRole(warn_dangling=True),
        "struct": XRefRole(warn_dangling=True),
        "enum": XRefRole(warn_dangling=True),
        "flags": XRefRole(warn_dangling=True),
        "type": XRefRole(warn_dangling=True),
        "field": XRefRole(warn_dangling=True),
        "enumvalue": XRefRole(warn_dangling=True),
    }
    initial_data = {
        "objects": {},   # name -> (docname, anchor, objtype)
        "groups": {},    # (model, group) -> (docname, anchor)
    }
    dangling_warnings = {
        t: "astb:%s reference target not found: %%(target)s" % t for t in roles
    }

    @property
    def objects(self):
        return self.data["objects"]

    @property
    def groups(self):
        return self.data["groups"]

    def note_object(self, name, objtype, node_id, location=None):
        docname = current_docname(self.env)
        if name in self.objects and self.objects[name][0] != docname:
            other = self.objects[name][0]
            logger.warning("duplicate astb %s %s, also documented in %s", objtype, name,
                           other, location=location)
        self.objects[name] = (docname, node_id, objtype)

    def note_group(self, model, group, node_id):
        self.groups[(model, group)] = (current_docname(self.env), node_id)

    def clear_doc(self, docname):
        for k, v in list(self.objects.items()):
            if v[0] == docname:
                del self.objects[k]
        for k, v in list(self.groups.items()):
            if v[0] == docname:
                del self.groups[k]

    def merge_domaindata(self, docnames, otherdata):
        for k, v in otherdata["objects"].items():
            if v[0] in docnames:
                self.objects[k] = v
        for k, v in otherdata["groups"].items():
            if v[0] in docnames:
                self.groups[k] = v

    def _find(self, typ, target):
        ent = self.objects.get(target)
        if ent is None:
            return None
        if typ == "type" and ent[2] not in ("class", "struct", "enum", "flags"):
            return None
        if typ == "enum" and ent[2] not in ("enum", "flags"):
            return None
        if typ not in ("type", "enum") and typ != ent[2]:
            return None
        return ent

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        if typ == "group":
            model, _, group = target.partition(":")
            ent = self.groups.get((model, group))
            if ent is None:
                return None
            return make_refnode(builder, fromdocname, ent[0], ent[1], contnode, target)
        ent = self._find(typ, target)
        if ent is None:
            return None
        return make_refnode(builder, fromdocname, ent[0], ent[1], contnode, target)

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):
        ent = self.objects.get(target)
        if ent is None:
            return []
        return [("astb:" + self.role_for_objtype(ent[2]),
                 make_refnode(builder, fromdocname, ent[0], ent[1], contnode, target))]

    def get_objects(self):
        for name, (docname, node_id, objtype) in self.objects.items():
            yield name, name, objtype, docname, node_id, 1

    def get_full_qualified_name(self, node):
        return node.get("reftarget")

    # -- for the diagram resolver -------------------------------------------

    def uri(self, builder, fromdocname, name, objtype=None):
        """A link from `fromdocname` to object `name`, or None."""
        ent = self.objects.get(name)
        if ent is None or (objtype and ent[2] != objtype):
            return None
        return _relative(builder, fromdocname, ent[0], ent[1])

    def group_uri(self, builder, fromdocname, model, group):
        ent = self.groups.get((model, group))
        if ent is None:
            return None
        return _relative(builder, fromdocname, ent[0], ent[1])


def _relative(builder, fromdoc, todoc, node_id):
    rel = builder.get_relative_uri(fromdoc, todoc)
    if not rel:
        # Same document: still name the file, because Sphinx rewrites
        # relative links inside SVG files to be relative to the image
        # directory, and a bare `#anchor` would become a directory link.
        import posixpath
        rel = posixpath.basename(builder.get_target_uri(todoc))
    return "%s#%s" % (rel, node_id)


def xref(objtype, target, text=None, warn=False, literal=True):
    """A pending cross-reference to `target`, as generated content (no
    warning if it does not resolve, unless `warn`)."""
    from sphinx import addnodes
    ref = addnodes.pending_xref(
        "", refdomain="astb", reftype=objtype, reftarget=target,
        refexplicit=text is not None, refwarn=warn)
    label = text if text is not None else target
    ref += nodes.literal(label, label) if literal else nodes.Text(label)
    return ref


def setup(app):
    app.add_domain(AstbDomain)
