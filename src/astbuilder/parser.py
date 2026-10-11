'''
Created on Sep 12, 2020

@author: ballance
'''
import yaml

from astbuilder.ast import Ast
from astbuilder.ast_class import AstClass
from .ast_struct import AstStruct
from astbuilder.ast_data import AstData
from astbuilder.ast_enum import AstEnum
from astbuilder.ast_flags import AstFlags
from astbuilder.type_list import TypeList
from astbuilder.type_map import TypeMap
from astbuilder.type_pointer import TypePointer, PointerKind
from astbuilder.type_scalar import TypeScalar, TypeKind
from astbuilder.type_userdef import TypeUserDef
from astbuilder import ast_class


class _LocDict(dict):
    """A YAML mapping that remembers its 1-based source line."""
    line = -1


class _LocStr(str):
    """A YAML string that remembers its 1-based source line."""
    line = -1


class _LocLoader(yaml.FullLoader):
    """FullLoader, plus the source line of every mapping and string.

    The values are still a dict and a str, so nothing that reads the parsed
    document can tell the difference; the line is only for documentation and
    error messages.
    """
    pass


def _construct_map(loader, node):
    loader.flatten_mapping(node)
    ret = _LocDict(loader.construct_pairs(node, deep=True))
    ret.line = node.start_mark.line + 1
    return ret


def _construct_str(loader, node):
    ret = _LocStr(loader.construct_scalar(node))
    ret.line = node.start_mark.line + 1
    if node.style in ("|", ">"):
        # A block scalar's text starts on the line after its indicator.
        ret.line += 1
    return ret


_LocLoader.add_constructor("tag:yaml.org,2002:map", _construct_map)
_LocLoader.add_constructor("tag:yaml.org,2002:str", _construct_str)

# The values `rel:` accepts on a raw-pointer field.
REL_VALUES = ("parent", "ref")


def _plain(v):
    """A YAML scalar without its line: plain str, or the value unchanged."""
    return str(v) if isinstance(v, str) else v


def _line(v):
    return getattr(v, "line", -1)


class Parser(object):
    
    def __init__(self, ast : Ast, filename : str = None):
        self.ast = ast
        self.filename = filename
    
    def _where(self, v):
        line = _line(v)
        if self.filename is None and line < 0:
            return ""
        return " (%s:%d)" % (self.filename or "<stream>", line)

    def _loc(self, ent, v):
        """Record the declaration site of `ent`, taken from the YAML value `v`."""
        ent.srcfile = self.filename
        ent.srcline = _line(v)

    def parse(self, f):
        if self.filename is None:
            self.filename = getattr(f, "name", None)
        doc = yaml.load(f, Loader=_LocLoader)
        
        for key in doc.keys():
            if key == "classes":
                self.parse_classes(doc["classes"])
            elif key == "structs":
                self.parse_structs(doc["structs"])
            elif key == "enums":
                self.parse_enums(doc["enums"])
            elif key == "flags":
                self.parse_flags(doc["flags"])
            else:
                raise Exception("Unknown section " + key)
            
        # Order some things to ensure predictable output
        self.ast.classes.sort(key=lambda x: x.name)
        self.ast.enums.sort(key=lambda x: x.name)
        self.ast.flags.sort(key=lambda x: x.name)
        self.ast.structs.sort(key=lambda x: x.name)
            
        return self.ast
    
    def parse_classes(self, classes):
        if classes is not None:
            if not isinstance(classes, list):
                raise Exception("Expect classes to be a list, not " + str(type(classes)) + " " + str(classes))
        
            for e in classes:
                self.ast.addClass(self.parse_class(e))
            
    def parse_class(self, cls):

        if isinstance(cls, str):
            ast_cls = AstClass(str(cls))
        elif isinstance(cls, dict):
            ast_cls = AstClass(str(next(iter(cls))))
            if ast_cls.name is None:
                raise Exception("Failed to get name from cls " + str(cls))
            if cls[ast_cls.name] is not None:
                root = cls[ast_cls.name]
                if isinstance(root, dict):
                    items = list(root.items())
                elif isinstance(root, list):
                    items = [next(iter(elem.items())) for elem in root]
                else:
                    items = []
                for key, val in items:
                    if key == "super":
                        ast_cls.super = TypeUserDef(str(val))
                    elif key == "data":
                        self.parse_class_data(ast_cls, val)
                    elif key == "doc":
                        ast_cls.doc = _plain(val)
                        ast_cls.docline = _line(val)
                    elif key == "set_by":
                        ast_cls.set_by = str(val)
                    else:
                        raise Exception("Unknown class key " + str(key)
                                        + self._where(key))
        else:
            raise Exception("Unknown class entity type " + str(cls))
                
        if ast_cls.name is None:
            raise Exception("No name provided for class")

        self._loc(ast_cls, cls)
        return ast_cls
                
    def parse_class_data(self, ast_cls, data):

        for elem in data:
            name = next(iter(elem)).strip()

            t = None
            is_ctor = True
            init = None
            visit = True
            doc = None
            docline = -1
            rel = None
            set_by = None
            item = elem[name]
            
            if isinstance(item, str):
                # Simple type signature
                t = self.parse_simple_type(item)
                attrs = []
            elif isinstance(item, list):
                # YAML packs as list of dicts
                attrs = [next(iter(it.items())) for it in item]
            elif isinstance(item, dict):
                attrs = list(item.items())
            else:
                raise Exception("Unknown type signature \"%s\" for field %s in class %s%s" % (
                    str(item), name, ast_cls.name, self._where(elem)))

            for key, val in attrs:
                if key == "type":
                    t = self.parse_simple_type(val)
                elif key == "is_ctor":
                    is_ctor = bool(val)
                elif key == "init":
                    init = str(val)
                elif key == "visit":
                    visit = bool(val)
                elif key == "doc":
                    # The field's own doc. This used to overwrite the
                    # *class's* doc (in this list form) or was rejected (in
                    # the mapping form).
                    doc = _plain(val)
                    docline = _line(val)
                elif key == "rel":
                    rel = str(val)
                elif key == "set_by":
                    set_by = str(val)
                else:
                    raise Exception("Unknown data-item key " + str(key) + self._where(key))

            if t is None:
                raise Exception("No type specified for field " + name + self._where(elem))

            if rel is not None:
                if rel not in REL_VALUES:
                    raise Exception("Field %s.%s: rel: must be one of %s, not \"%s\"%s" % (
                        ast_cls.name, name, ", ".join(REL_VALUES), rel, self._where(elem)))
                target = t.t if isinstance(t, TypeList) else t
                if not (isinstance(target, TypePointer) and target.pt == PointerKind.Raw):
                    raise Exception("Field %s.%s: rel: applies only to P<T> and list<P<T>> fields%s" % (
                        ast_cls.name, name, self._where(elem)))

            is_ctor &= not isinstance(t, TypeList)
            d = AstData(str(name), t, is_ctor)
            d.init = init
            d.visit = visit
            d.doc = doc
            d.docline = docline
            d.rel = rel
            d.set_by = set_by
            self._loc(d, elem)
            ast_cls.data.append(d)

    def parse_structs(self, structs):
        if structs is not None:
            if not isinstance(structs, list):
                raise Exception("Expect structs to be a list, not " + str(type(structs)) + " " + str(structs))
        
            for e in structs:
                self.ast.addStruct(self.parse_struct(e))
            
    def parse_struct(self, cls):

        if isinstance(cls, str):
            ast_cls = AstStruct(str(cls))
        elif isinstance(cls, dict):
            ast_cls = AstStruct(str(next(iter(cls))))
            if ast_cls.name is None:
                raise Exception("Failed to get name from cls " + str(cls))
            if cls[ast_cls.name] is not None:
                root = cls[ast_cls.name]
                if isinstance(root, dict):
                    for key in root.keys():
                        if key == "data":
                            self.parse_class_data(ast_cls, root[key])
                        elif key == "doc":
                            ast_cls.doc = _plain(root[key])
                            ast_cls.docline = _line(root[key])
                        else:
                            raise Exception("Unknown class key " + str(key))
                elif isinstance(root, list):
                    for elem in cls[ast_cls.name]:
                        key = next(iter(elem))
                        if key == "data":
                            self.parse_class_data(ast_cls, elem[key])
                        elif key == "doc":
                            ast_cls.doc = _plain(elem[key])
                            ast_cls.docline = _line(elem[key])
                        else:
                            raise Exception("Unknown class key " + str(key))
        else:
            raise Exception("Unknown class entity type " + str(cls))
                
        if ast_cls.name is None:
            raise Exception("No name provided for class")

        self._loc(ast_cls, cls)
        return ast_cls
                

    def parse_simple_type(self, item):
        ret = None
        
        primitive_m = {
            "string" : TypeScalar(TypeKind.String),
            "bool" : TypeScalar(TypeKind.Bool),
            "uint8_t" : TypeScalar(TypeKind.Uint8),
            "int8_t" : TypeScalar(TypeKind.Int8),
            "uint16_t" : TypeScalar(TypeKind.Uint16),
            "int16_t" : TypeScalar(TypeKind.Int16),
            "uint32_t" : TypeScalar(TypeKind.Uint32),
            "int32_t" : TypeScalar(TypeKind.Int32),
            "uint64_t" : TypeScalar(TypeKind.Uint64),
            "int64_t" : TypeScalar(TypeKind.Int64),
            "float" : TypeScalar(TypeKind.Float32),
            "double" : TypeScalar(TypeKind.Float64)
            }
        
        if item in primitive_m.keys():
            ret = primitive_m[item]
        elif item.startswith("SP<"):
            # Shared pointer
            core_type = item[item.find('<')+1:item.rfind('>')]
            ret = TypePointer(PointerKind.Shared, self.parse_simple_type(core_type))
        elif item.startswith("UP<"):
            core_type = item[item.find('<')+1:item.rfind('>')]
            ret = TypePointer(PointerKind.Unique, self.parse_simple_type(core_type))
        elif item.startswith("P<"):
            core_type = item[item.find('<')+1:item.rfind('>')]
            ret = TypePointer(PointerKind.Raw, self.parse_simple_type(core_type))
        elif item.startswith("list<"):
            core_type = item[item.find('<')+1:item.rfind('>')]
            ret = TypeList(self.parse_simple_type(core_type))
        elif item.startswith("map<"):
            key_type = item[item.find('<')+1:item.rfind(',')].strip()
            val_type = item[item.rfind(',')+1:item.rfind('>')].strip()
            ret = TypeMap(
                self.parse_simple_type(key_type),
                self.parse_simple_type(val_type))
        else:
            # Assume a user-defined type
            ret = TypeUserDef(str(item))
            
        return ret
    
    def parse_enums(self, enums):
        
        for enum in enums:
            ast_e = AstEnum(str(next(iter(enum.keys()))))
            self._loc(ast_e, enum)

            for e in enum[ast_e.name]:
                name = self.parse_enum_value(ast_e, e)
                ast_e.values.append((name, None))
            
            self.ast.addEnum(ast_e)

    def parse_enum_value(self, ent, v):
        """One enum or flags value, in any of the three forms:

            - Name                          bare
            - Name: "what it means"         short: the string is the doc
            - Name: {doc: "what it means"}  long

        Records the doc and line on `ent` and returns the name. `value:` (an
        explicit number) is rejected for now: gen-reflect, gen-wasm and
        gen-census all assume a value's number is its position.
        """
        if isinstance(v, str):
            name, body = str(v), None
        elif isinstance(v, dict) and len(v) == 1:
            name, body = str(next(iter(v))), next(iter(v.values()))
        else:
            raise Exception("Unknown %s value entry: %s%s" % (ent.name, str(v), self._where(v)))

        doc = None
        if body is None:
            pass
        elif isinstance(body, str):
            doc = str(body)
        elif isinstance(body, dict):
            for key, val in body.items():
                if key == "doc":
                    doc = str(val)
                elif key == "value":
                    raise Exception("%s.%s: explicit value: is not supported; values are "
                                    "numbered by position%s" % (ent.name, name, self._where(v)))
                else:
                    raise Exception("%s.%s: unknown value key %s%s" % (
                        ent.name, name, str(key), self._where(key)))
        else:
            raise Exception("%s.%s: expected a doc string or a mapping, not %s%s" % (
                ent.name, name, str(body), self._where(v)))

        if doc is not None:
            ent.value_docs[name] = doc
            ent.value_doclines[name] = _line(body) if isinstance(body, str) else _line(
                body.get("doc"))
        ent.value_lines[name] = _line(v)
        return name
            
    def parse_flags(self, flags):
        
        for f in flags:
#            print("flag: " + str(f))
            ast_f = AstFlags(str(next(iter(f.keys()))))
            self._loc(ast_f, f)
        
            for fv in f[ast_f.name]:
                ast_f.values.append(self.parse_enum_value(ast_f, fv))
            
            self.ast.addFlags(ast_f)
        
