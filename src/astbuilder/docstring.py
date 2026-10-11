'''
Reading a class's `doc:` text: the sections documentation tools treat
specially.

Model authors often write a class's doc Google-style, describing the fields
in the class doc rather than on each field:

    Root of a resolved symbol tree.

    Attributes:
        units: Compilation units linked into this tree
        filenames: Maps file IDs to their paths

    See Also:
        SymbolScope, GlobalScope

split() takes that apart: the body (everything else, unchanged), the
attribute descriptions by name (used where a field has no `doc:` of its
own, including for inherited fields the class describes in its own terms),
and the See Also lines (whose names are rendered as links).
'''
import dataclasses as dc
import re
from typing import Dict, List

_HEADER = re.compile(r"^(?P<indent>\s*)(?P<name>Attributes|Fields|See Also)\s*:\s*$")
_ATTR = re.compile(r"^(?P<name>\w+)\s*(?:\([^)]*\))?\s*:\s*(?P<text>.*)$")


@dc.dataclass
class DocParts:
    body: str
    attributes: Dict[str, str] = dc.field(default_factory=dict)
    #: The section's lines, stripped; usually `Name, Name.field, ...`.
    see_also: List[str] = dc.field(default_factory=list)


def _indent(line):
    return len(line) - len(line.lstrip())


def split(doc: str) -> DocParts:
    if not doc:
        return DocParts(doc or "")
    lines = doc.split("\n")
    body, attrs, see = [], {}, []
    i = 0
    while i < len(lines):
        m = _HEADER.match(lines[i])
        if m is None:
            body.append(lines[i])
            i += 1
            continue
        base = len(m.group("indent"))
        block = []
        i += 1
        while i < len(lines) and (not lines[i].strip() or _indent(lines[i]) > base):
            block.append(lines[i])
            i += 1
        if m.group("name") == "See Also":
            see.extend(ln.strip() for ln in block if ln.strip())
            continue
        # Attributes / Fields: `name: text`, continued by deeper lines.
        sub = min((_indent(ln) for ln in block if ln.strip()), default=0)
        key = None
        for ln in block:
            if not ln.strip():
                continue
            am = _ATTR.match(ln.strip()) if _indent(ln) == sub else None
            if am:
                key = am.group("name")
                attrs[key] = am.group("text").strip()
            elif key is not None:
                attrs[key] = (attrs[key] + " " + ln.strip()).strip()
    while body and not body[-1].strip():
        body.pop()
    return DocParts("\n".join(body), attrs, see)


_BACKTICK = re.compile(r"(?<![`:\w])`([^`\n]+)`(?![`_\w])")


def backticks_to_literal(text: str) -> str:
    """`x` -> ``x``: single backticks as code, the Markdown habit, instead
    of reST's default role. Leaves ``literals``, :role:`targets`, `links`_
    and literal blocks (the indented block after a `::` line) alone."""
    if not text:
        return text
    out = []
    block = None        # indentation of the `::` line whose block we are in
    pending = None      # indentation of a `::` line whose block has not started
    for line in text.split("\n"):
        if block is not None:
            if not line.strip() or _indent(line) > block:
                out.append(line)
                continue
            block = None
        if pending is not None:
            if not line.strip():
                out.append(line)
                continue
            if _indent(line) > pending:
                block, pending = pending, None
                out.append(line)
                continue
            pending = None
        out.append(_BACKTICK.sub(lambda m: "``%s``" % m.group(1), line))
        if line.rstrip().endswith("::"):
            pending = _indent(line)
    return "\n".join(out)


def names(line: str) -> List[str]:
    """The comma-separated names in a See Also line, or [] when the line is
    prose: any item that is not one identifier or `Class.field`."""
    toks = [t.strip() for t in line.strip().rstrip(".").split(",")]
    if toks and all(re.fullmatch(r"\w+(\.\w+)?", t) for t in toks):
        return toks
    return []
