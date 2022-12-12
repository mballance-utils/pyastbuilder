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


class Parser(object):
    
    def __init__(self, ast : Ast):
        self.ast = ast
        pass
    
    def parse(self, f):
        doc = yaml.load(f, Loader=yaml.FullLoader)            
        
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
            
        return self.ast
    
    def parse_classes(self, classes):
        if classes is not None:
            if not isinstance(classes, list):
                raise Exception("Expect classes to be a list, not " + str(type(classes)) + " " + str(classes))
        
            for e in classes:
                self.ast.addClass(self.parse_class(e))
            
    def parse_class(self, cls):

        if isinstance(cls, str):
            ast_cls = AstClass(cls)
        elif isinstance(cls, dict):
            ast_cls = AstClass(next(iter(cls)))
            if ast_cls.name is None:
                raise Exception("Failed to get name from cls " + str(cls))
            if cls[ast_cls.name] is not None:
                root = cls[ast_cls.name]
                if isinstance(root, dict):
                    print("DICT")
                    for key in root.keys():
                        if key == "super":
                            ast_cls.super = TypeUserDef(root[key])
                        elif key == "data":
                            self.parse_class_data(ast_cls, root[key])
                        else:
                            raise Exception("Unknown class key " + str(key))
                elif isinstance(root, list):
                    for elem in cls[ast_cls.name]:
                        key = next(iter(elem))
                        if key == "super":
                            ast_cls.super = TypeUserDef(elem[key])
                        elif key == "data":
                            self.parse_class_data(ast_cls, elem[key])
                        else:
                            raise Exception("Unknown class key " + str(key))
        else:
            raise Exception("Unknown class entity type " + str(cls))
                
        if ast_cls.name is None:
            raise Exception("No name provided for class")
                
        return ast_cls
                
    def parse_class_data(self, ast_cls, data):

        print("parse_class_data: %s" % ast_cls.name)        
        for elem in data:
            name = next(iter(elem)).strip()

            t = None
            is_ctor = True
            init = None
            visit = True
            item = elem[name]
            
            if isinstance(item, str):
                # Simple type signature
                t = self.parse_simple_type(item)
            elif isinstance(item, list):
                # YAML packs as list of dicts
                for it in item:
                    key = next(iter(it))
                    if key == "type":
                        t = self.parse_simple_type(it[key])
                    elif key == "is_ctor":
                        is_ctor = bool(it['is_ctor'])
                    elif key == "init":
                        init = str(it['init'])
                    elif key == "visit":
                        visit = bool(it['visit'])
                    else:
                        raise Exception("Unknown data-item key " + key)
                    
                if t is None:
                    raise Exception("No type specified for field " + name)
            elif isinstance(item, dict):
                for key in item.keys():
                    if key == "type":
                        t = self.parse_simple_type(item[key])
                    elif key == "is_ctor":
                        is_ctor = bool(item['is_ctor'])
                    elif key == "init":
                        init = str(item['init'])
                    elif key == "visit":
                        visit = bool(item['visit'])
                    else:
                        raise Exception("Unknown data-item key " + key)
                if t is None:
                    raise Exception("No type specified for field " + name)
            else:
                raise Exception("Unknown type signature \"%s\" for field %s in class %s" % (
                    str(item), name, ast_cls.name))

            is_ctor &= not isinstance(t, TypeList)
            d = AstData(name, t, is_ctor)
            d.init = init
            d.visit = visit
            ast_cls.data.append(d)

    def parse_structs(self, structs):
        if structs is not None:
            if not isinstance(structs, list):
                raise Exception("Expect structs to be a list, not " + str(type(structs)) + " " + str(structs))
        
            for e in structs:
                self.ast.addStruct(self.parse_struct(e))
            
    def parse_struct(self, cls):

        if isinstance(cls, str):
            ast_cls = AstStruct(cls)
        elif isinstance(cls, dict):
            ast_cls = AstStruct(next(iter(cls)))
            if ast_cls.name is None:
                raise Exception("Failed to get name from cls " + str(cls))
            if cls[ast_cls.name] is not None:
                root = cls[ast_cls.name]
                if isinstance(root, dict):
                    print("DICT")
                    for key in root.keys():
                        if key == "data":
                            self.parse_class_data(ast_cls, root[key])
                        else:
                            raise Exception("Unknown class key " + str(key))
                elif isinstance(root, list):
                    for elem in cls[ast_cls.name]:
                        key = next(iter(elem))
                        if key == "data":
                            self.parse_class_data(ast_cls, elem[key])
                        else:
                            raise Exception("Unknown class key " + str(key))
        else:
            raise Exception("Unknown class entity type " + str(cls))
                
        if ast_cls.name is None:
            raise Exception("No name provided for class")

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
            "int64_t" : TypeScalar(TypeKind.Int64)
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
            print("key_type: " + key_type)
            print("val_type: " + val_type)
            ret = TypeMap(
                self.parse_simple_type(key_type),
                self.parse_simple_type(val_type))
        else:
            # Assume a user-defined type
            ret = TypeUserDef(item)
            
        return ret
    
    def parse_enums(self, enums):
        
        for enum in enums:
            print("enum: " + str(enum))
#            ast_e = AstEnum(enum['name'].strip())
            ast_e = AstEnum(next(iter(enum.keys())))

            # TODO: what about specific values        
            for e in enum[ast_e.name]:
#                ev = enum['values'][e]
                ast_e.values.append((e,None))
            
            self.ast.addEnum(ast_e)
            
    def parse_flags(self, flags):
        
        for f in flags:
#            print("flag: " + str(f))
            ast_f = AstFlags(next(iter(f.keys())))
        
            for fv in f[ast_f.name]:
#                print("fv: %s" % str(fv))
                if isinstance(fv, str):
                    ast_f.values.append(fv)
                elif isinstance(fv, dict):
                    ast_f.values.append(next(iter(fv)))
                else:
                    raise Exception("Unknown flags entry: " + str(fv))
            
            self.ast.addFlags(ast_f)
        
