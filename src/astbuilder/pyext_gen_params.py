'''
Created on May 28, 2022

@author: mballance
'''
from astbuilder.pyext_type_name_gen import PyExtTypeNameGen
from astbuilder.type_userdef import TypeUserDef
from astbuilder.ast_enum import AstEnum

class PyExtGenParams(object):
    
    @classmethod
    def gen_ctor_param_temps(cls, c, out):
        if c.super is not None:
            # Recurse first
            cls.gen_ctor_param_temps(c.super.target, out)
            
        params = list(filter(lambda d : d.is_ctor, c.data))
        for p in params:
            if isinstance(p.t, TypeUserDef) and isinstance(p.t.target, AstEnum):
                out.println("cdef int %s_i = int(%s)" % (p.name, p.name))
    
    @classmethod
    def gen_ctor_params(cls, c, out, is_decl, ins_self):
        """Returns True if this level (or a previous level) added content"""
        ret = False
            
        if c.super is not None:
            # Recurse first
            ret |= cls.gen_ctor_params(c.super.target, out, is_decl, ins_self)
            
        if ins_self and not ret:
            out.write("self")
            ret = True
            
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
    def gen_ctor_pvals(cls, name, c, out):
        ret = False
        if c.super is not None:
            # Recurse first
            ret |= cls.gen_ctor_pvals(name, c.super.target, out)
            
        params = list(filter(lambda d : d.is_ctor, c.data))
        for i,p in enumerate(params):
            if ret and i == 0:
                out.write(",\n")
            out.write(out.ind)
            if isinstance(p.t, TypeUserDef) and isinstance(p.t.target, AstEnum):
                if i+1<len(params):
                    t=",\n"
                else:
                    t=""
                    
                out.write("<%s_decl.%s>(%s_i)%s" % (
                    name,
                    p.t.target.name,
                    p.name,
                    t))
            else:
                out.write(p.name + (",\n" if i+1 < len(params) else ""))
            ret = True
        
        return ret