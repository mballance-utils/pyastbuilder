'''
The spelling rules every backend shares.

An accessor's name is derived from its field's name by a few small rules
(`count` -> `getCount`, `children` -> `getChild(i)` / `numChildren()`). Each
generator used to spell them inline, dozens of times; they live here so the
generators and the documentation (astbuilder.projection, astbuilder.sphinx)
cannot disagree about what a field is called.

Change a rule here and every generated API changes with it -- which is the
point, and also why the pssparser snapshot gate
(scripts/astbuilder_snapshot.py) must show no difference after a refactoring
that only moves code onto these functions.
'''


def cap(name: str) -> str:
    """`count` -> `Count`: the stem of `get<Stem>`/`set<Stem>`."""
    return name[0].upper() + name[1:]


def singular(name: str) -> str:
    """The element stem of a list accessor: `Children` -> `Child`,
    `Items` -> `Item`; anything else is unchanged (`Path` -> `Path`).

    Takes and returns the capitalised stem (`cap(field)`).
    """
    if name.endswith("ren"):
        return name[:-3]
    if name.endswith("s"):
        return name[:-1]
    return name


def plural(name: str) -> str:
    """The whole-list stem: a name that already reads as a plural is kept
    (`Children`, `Items`); any other gets `List` (`Path` -> `PathList`).

    Takes and returns the capitalised stem (`cap(field)`).
    """
    if name.endswith("ren") or name.endswith("s"):
        return name
    return name + "List"
