'''
Created on May 28, 2022

@author: mballance
'''
from astbuilder.pyext_type_name_gen import PyExtTypeNameGen

class PyExtGenParams(object):
    
    @classmethod
    def gen_ctor_params(cls, c, out, is_decl, ins_self):
        """Returns True if this level (or a previous level) added content"""
        ret = False
            
        if c.super is not None:
            # Recurse first
            ret |= cls.gen_ctor_params(c.super.target, out, is_decl, ins_self)
            
        if ins_self and not ret:
            out.write("self")
            
        if is_decl:
            is_pytype=False
            is_pydecl=True
        else:
            is_pytype=True
            is_pydecl=False
            
        params = list(filter(lambda d : d.is_ctor, c.data))
        for i,p in enumerate(params):
            if i == 0:
                if ret:
                    out.write(",\n")
                elif ins_self:
                    out.write(",\n")
            out.write(out.ind)
            out.write(PyExtTypeNameGen(
                compressed=True,
                is_pytype=is_pytype,
                is_pydecl=is_pydecl,
                is_ret=True).gen(p.t) + " ")
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