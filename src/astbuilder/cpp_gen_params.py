'''
Created on May 28, 2022

@author: mballance
'''
from astbuilder.cpp_type_name_gen import CppTypeNameGen

class CppGenParams(object):
    
    @classmethod
    def gen_ctor_params(cls, c, out):
        """Returns True if this level (or a previous level) added content"""
        ret = False
        if c.super is not None:
            # Recurse first
            ret |= cls.gen_ctor_params(c.super.target, out)
            
        params = list(filter(lambda d : d.is_ctor, c.data))
        for i,p in enumerate(params):
            if ret and i == 0:
                out.write(",\n")
            out.write(out.ind)
            out.write(CppTypeNameGen(compressed=True,is_ret=True).gen(p.t) + " ")
            out.write(p.name + (",\n" if i+1 < len(params) else ""))
            ret = True
        
        return ret        
    
    @classmethod
    def gen_ctor_pvals(cls, c, out):
        ret = False
        if c.super is not None:
            # Recurse first
            ret |= cls.gen_ctor_pvals(c.super.target, out)
            
        params = list(filter(lambda d : d.is_ctor, c.data))
        for i,p in enumerate(params):
            if ret and i == 0:
                out.write(",\n")
            out.write(out.ind)
            out.write(p.name + (",\n" if i+1 < len(params) else ""))
            ret = True
        
        return ret        