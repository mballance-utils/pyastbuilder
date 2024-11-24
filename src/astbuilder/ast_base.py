
import dataclasses as dc

@dc.dataclass
class AstBase(object):
    name : str
    doc : str = None