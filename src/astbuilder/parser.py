'''
Created on Sep 12, 2020

@author: ballance
'''
import json

from astgen.ast import Ast
from astgen.ast_class import AstClass
from astgen.ast_data import AstData
from astgen.type_list import TypeList
from astgen.type_pointer import TypePointer, PointerKind
from astgen.type_scalar import TypeScalar
from astgen.type_userdef import TypeUserDef


class Parser(object):
    
    def __init__(self):
        pass
    
    def parse(self, file):
        self.ast = Ast()
        with open(file, "r") as fp:
            content = fp.read()
            
        print("content=" + str(content))
        
        doc = json.loads(content)
        
        for key in doc.keys():
            if key == "classes":
                self.parse_classes(doc["classes"])
                
            print("key=" + str(key))
            
        return self.ast
    
    def parse_classes(self, classes):
        if not isinstance(classes, list):
            raise Exception("Expect classes to be a list")
        
        for e in classes:
            self.ast.classes.append(self.parse_class(e))
            
    def parse_class(self, cls):
        ast_cls = AstClass()
        
        for key in cls.keys():
            if key == "name":
                ast_cls.name = cls[key]
            elif key == "super":
                ast_cls.super = cls[key]
            elif key == "data":
                self.parse_class_data(ast_cls, cls[key])
                
        if ast_cls.name is None:
            raise Exception("No name provided for class")
                
        return ast_cls
                
    def parse_class_data(self, ast_cls, data):
        
        for key in data.keys():
            item = data[key]
            print("item: " + key + " data: " + str(item))
            if isinstance(item, str):
                # Simple type signature
                t = self.parse_simple_type(item)
            else:
                raise Exception("Unknown type signature")

            ast_cls.data.append(AstData(key, t))

    def parse_simple_type(self, item):
        ret = None
        
        primitive_m = {
            "string" : TypeScalar(TypeScalar.String),
            "uint8_t" : TypeScalar(TypeScalar.Uint8),
            "int8_t" : TypeScalar(TypeScalar.Int8),
            "uint16_t" : TypeScalar(TypeScalar.Uint16),
            "int16_t" : TypeScalar(TypeScalar.Int16),
            "uint32_t" : TypeScalar(TypeScalar.Uint32),
            "int32_t" : TypeScalar(TypeScalar.Int32),
            "uint64_t" : TypeScalar(TypeScalar.Uint64),
            "int64_t" : TypeScalar(TypeScalar.Int64)
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
            
        
        