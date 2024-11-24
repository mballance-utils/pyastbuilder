#****************************************************************************
#* py_ext_map_accessor_gen.py
#*
#* Copyright 2023 Matthew Ballance and Contributors
#*
#* Licensed under the Apache License, Version 2.0 (the "License"); you may 
#* not use this file except in compliance with the License.  
#* You may obtain a copy of the License at:
#*
#*   http://www.apache.org/licenses/LICENSE-2.0
#*
#* Unless required by applicable law or agreed to in writing, software 
#* distributed under the License is distributed on an "AS IS" BASIS, 
#* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
#* See the License for the specific language governing permissions and 
#* limitations under the License.
#*
#* Created on:
#*     Author: 
#*
#****************************************************************************
from astbuilder.visitor import Visitor
from astbuilder.type_pointer import PointerKind
from astbuilder.type_scalar import TypeKind
from astbuilder.pyext_type_name_gen import PyExtTypeNameGen
from astbuilder.type_map import TypeMap
from astbuilder.pyext_call_param_gen import PyExtCallParamGen
from astbuilder.pyext_rval_gen import PyExtRvalGen

class PyExtMapAccessorGen(Visitor):

    def __init__(self, name, clsname, decl_pxd, pxd, pyx, pyi):
        super().__init__()
        self.name = name
        self.clsname = clsname
        self.pxd = pxd
        self.decl_pxd = decl_pxd
        self.pyx = pyx
        self.pyi = pyi
        self.field = None
        self.tgen_decl_decl = PyExtTypeNameGen(
            ns=self.name,
            compressed=True,
            is_pytype=False,
            is_pydecl=False,
            is_ref=False,
            is_const=False)
        self.tgen_decl = PyExtTypeNameGen(
            ns=self.name,
            compressed=True,
            is_pytype=False,
            is_pydecl=True,
            is_ref=False,
            is_const=False)
        self.tgen_py = PyExtTypeNameGen(
            ns=self.name,
            compressed=True,
            is_pytype=True,
            is_pydecl=False,
            is_ref=False,
            is_const=False)

        pass

    def gen(self, field, t : TypeMap):
        self.field = field
        self.mtype = t
        cname = self.field.name[0].upper() + self.field.name[1:]
#        t.vt.accept(self)
        # Generate C++ import
        self.decl_pxd.println("std_unordered_map[%s,%s] &get%s()" % (
            self.tgen_decl_decl.gen(t.kt),
            self.tgen_decl_decl.gen(t.vt),
            cname
        ))
        self._hasKey(t)
        self._getItem(t)
        pass

    def visitTypeScalar(self, t):
        """Value-type is a scalar"""
        print("map-scalar accessor")
        return super().visitTypeScalar(t)

    def visitTypePointer(self, t):
        """Value-type is a pointer"""
        print("mapp-pointer accessor")
#        self._getAsIterator(t)
#        self._getAsList(t)
#        self._getAt(t)
#        self._addItem(t)
#        self._getSize(t)

    def _getAsList(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        pname = name
        tname = t.t.name

        if not pname.endswith("ren") and not pname.endswith("s"):
            pname += "List"

        self.pxd.println("cpdef get%s(self)" % pname)
        
        self.pyx.println("cpdef get%s(self):" % pname)
        self.pyx.inc_indent()

        if t.pt == PointerKind.Raw:
            self.pyx.println("cdef const std_vector[%s_decl.I%sP] *__lp = &self.as%s().get%s()" % (
                self.name, tname, self.clsname, name))
        elif t.pt == PointerKind.Unique:
            self.pyx.println("cdef const std_vector[%s_decl.I%sUP] *__lp = &self.as%s().get%s()" % (
                self.name, tname, self.clsname, name))
        elif t.pt == PointerKind.Shared:
            pass
        else:
            raise Exception("Accessor generation not supported for " + str(self.pt))
        self.pyx.println("cdef %s_decl.I%s *__ep;" % (self.name, tname))
        self.pyx.println("ret = []")
        self.pyx.println("of = ObjFactory()")

        self.pyx.println("for __i in range(__lp.size()):")
        self.pyx.inc_indent()
        if t.pt == PointerKind.Raw:
            self.pyx.println("__ep = __lp.at(__i)")
        elif t.pt == PointerKind.Unique:
            self.pyx.println("__ep = __lp.at(__i).get()")
        elif t.pt == PointerKind.Shared:
#            self.gen_sptr_accessors(t)
            pass
        else:
            raise Exception("Accessor generation not supported for " + str(self.pt))
        self.pyx.println("ret.append(__ep.accept(of._hndl))")
        self.pyx.dec_indent()
        self.pyx.println("return ret")
        self.pyx.dec_indent()

    def _hasKey(self, t : TypeMap):
        name = self.field.name
        cname = self.field.name[0].upper() + self.field.name[1:]
        pname = name
        if pname.endswith("ren"):
            pname = name[:-3]
        elif pname.endswith("s"):
            pname = name[:-1]
#        tname = t.t.name

        self.pxd.println("cpdef bool %sHas(self, %s i)" % (
            name,
            self.tgen_py.gen(t.kt)))

        self.pyx.println("cpdef bool %sHas(self, %s i):" % (
            name,
            self.tgen_py.gen(t.kt)))
        self.pyx.inc_indent()

        self.pyx.println("cdef std_unordered_map[%s,%s].const_iterator it = self.as%s().get%s().find(%s)" % (
            self.tgen_decl.gen(t.kt),
            self.tgen_decl.gen(t.vt),
            self.clsname,
            cname,
            PyExtCallParamGen(self.name).gen("i", t.kt)))
        self.pyx.println("return (it != self.as%s().get%s().end())" % (
            self.clsname,
            cname))

        self.pyx.dec_indent()

    def _getItem(self, t : TypeMap):
        name = self.field.name
        cname = self.field.name[0].upper() + self.field.name[1:]
        pname = name
        if pname.endswith("ren"):
            pname = name[:-3]
        elif pname.endswith("s"):
            pname = name[:-1]

        self.pxd.println("cpdef %s %sAt(self, %s i)" % (
            self.tgen_py.gen(t.vt),
            name,
            self.tgen_py.gen(t.kt)))

        self.pyx.println("cpdef %s %sAt(self, %s i):" % (
            self.tgen_py.gen(t.vt),
            name,
            self.tgen_py.gen(t.kt)))
        self.pyx.inc_indent()

        self.pyx.println("cdef std_unordered_map[%s,%s].const_iterator it = self.as%s().get%s().find(%s)" % (
            self.tgen_decl.gen(t.kt),
            self.tgen_decl.gen(t.vt),
            self.clsname,
            cname,
            PyExtCallParamGen(self.name).gen("i", t.kt)))

        PyExtRvalGen(self.name, self.pyx).gen("dereference(it).second", t.vt)

        self.pyx.dec_indent()

    def _addItem(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        pname = name
        if pname.endswith("ren"):
            pname = name[:-3]
        elif pname.endswith("s"):
            pname = name[:-1]
        tname = t.t.name

        self.pxd.println("cpdef void add%s(self, %s i)" % (pname, tname))
        
        self.pyx.println("cpdef void add%s(self, %s i):" % (pname, tname))
        self.pyx.inc_indent()
        if t.pt == PointerKind.Raw:
            self.pyx.println("self.as%s().get%s().push_back(i.as%s())" % (
                self.clsname, name, tname))
        elif t.pt == PointerKind.Unique:
            self.pyx.println("i._owned = False")
            self.pyx.println("self.as%s().get%s().push_back(%s_decl.I%sUP(i.as%s(), True))" % (
                self.clsname, name, self.name, tname, tname))

        # if t.pt == PointerKind.Raw:
        #     self.pyx.println("cdef %s_decl.I%s *__ep = self.as%s().get%s().at(i);" % (
        #         self.name, tname, self.clsname, name))
        # elif t.pt == PointerKind.Unique:
        #     self.pyx.println("cdef %s_decl.I%s *__ep = self.as%s().get%s().at(i).get();" % (
        #         self.name, tname, self.clsname, name))
        # elif t.pt == PointerKind.Shared:
        #     pass
        # else:
        #     raise Exception("Accessor generation not supported for " + str(self.pt))
        # self.pyx.println("of = ObjFactory()")
        # self.pyx.println("__ep.accept(of._hndl)")

        # self.pyx.println("return of._obj")
        self.pyx.dec_indent()

    def _getSize(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        tname = t.t.name

        self.pxd.println("cpdef num%s(self)" % name)
        
        self.pyx.println("cpdef num%s(self):" % name)
        self.pyx.inc_indent()

        self.pyx.println("return self.as%s().get%s().size()" % (
            self.clsname, name))
        self.pyx.dec_indent()
