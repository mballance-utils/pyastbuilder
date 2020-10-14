'''
Created on Sep 12, 2020

@author: ballance
'''
import json

from astbuilder.ast import Ast
from astbuilder.ast_class import AstClass
from astbuilder.ast_data import AstData
from astbuilder.type_list import TypeList
from astbuilder.type_pointer import TypePointer, PointerKind
from astbuilder.type_scalar import TypeScalar, TypeKind
from astbuilder.type_userdef import TypeUserDef
from astbuilder.ast_enum import AstEnum


class Parser(object):
    
    def __init__(self, ast : Ast):
        self.ast = ast
        pass
    
    def parse(self, file):
        with open(file, "r") as fp:
            content = fp.read()
            
        doc = json.loads(content)
        
        for key in doc.keys():
            if key == "classes":
                self.parse_classes(doc["classes"])
            elif key == "enums":
                self.parse_enums(doc["enums"])
            else:
                raise Exception("Unknown section " + key)
            
        return self.ast
    
    def parse_classes(self, classes):
        if not isinstance(classes, list):
            raise Exception("Expect classes to be a list")
        
        for e in classes:
            self.ast.addClass(self.parse_class(e))
            
    def parse_class(self, cls):
        ast_cls = AstClass()
        
        for key in cls.keys():
            if key == "name":
                ast_cls.name = cls[key].strip()
            elif key == "super":
                ast_cls.super = TypeUserDef(cls[key].strip())
            elif key == "data":
                self.parse_class_data(ast_cls, cls[key])
                
        if ast_cls.name is None:
            raise Exception("No name provided for class")
                
        return ast_cls
                
    def parse_class_data(self, ast_cls, data):
        
        for key in data.keys():
            is_ctor = True
            init = None
            item = data[key]
            if isinstance(item, str):
                # Simple type signature
                t = self.parse_simple_type(item)
            elif isinstance(item, dict):
                t = self.parse_simple_type(item['type'])
                if 'is_ctor' in item.keys():
                    is_ctor = bool(item['is_ctor'])
                if 'init' in item.keys():
                    init = str(item['init'])
            else:
                raise Exception("Unknown type signature")

            is_ctor &= not isinstance(t, TypeList)
            d = AstData(key, t, is_ctor)
            d.init = init
            ast_cls.data.append(d)

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
        else:
            # Assume a user-defined type
            ret = TypeUserDef(item)
            
        return ret
    
    def parse_enums(self, enums):
        
        for enum in enums:
            ast_e = AstEnum(enum['name'].strip())
        
            for e in enum['values'].keys():
                ev = enum['values'][e]
                ast_e.values.append((e,ev))
            
            self.ast.addEnum(ast_e)
        
        