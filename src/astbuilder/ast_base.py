
import dataclasses as dc

@dc.dataclass
class AstBase(object):
    name : str
    doc : str = None
    # Where the entity is declared: the YAML file (None when parsed from a
    # stream with no name) and the 1-based line.
    srcfile : str = None
    srcline : int = -1
    # The 1-based line where the `doc:` text starts, or -1.
    docline : int = -1