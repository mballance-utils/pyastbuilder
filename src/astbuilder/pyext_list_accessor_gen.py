#****************************************************************************
#* py_ext_list_accessor_gen.py
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

class PyExtListAccessorGen(Visitor):

    def __init__(self, name, clsname, decl_pxd, pxd, pyx):
        super().__init__()
        self.name = name
        self.clsname = clsname
        self.pxd = pxd
        self.decl_pxd = decl_pxd
        self.pyx = pyx
        self.field = None

        pass

    def gen(self, field, t):
        self.field = field
        t.accept(self)
        pass

    def visitTypePointer(self, t):
        print("list-pointer accessor")
#        self._getAsIterator(t)
        self._getAsList(t)
        self._getAt(t)
        self._getSize(t)

#     def _getAsIterator(self, t):
#         name = self.field.name[0].upper() + self.field.name[1:]
#         tname = t.t.name

#         self.pxd.println("cpdef get%s(self)" % name)
        
#         self.pyx.println("cpdef get%s(self):" % name)
#         self.pyx.inc_indent()
#         self.pyx.println()
#         self.pyx.println("class Iterator(object):")
#         self.pyx.inc_indent()
#         self.pyx.println("pass")
#         self.pyx.dec_indent()

#         if t.pt == PointerKind.Raw:
#             self.pyx.println("cdef const std_vector[%s_decl.I%sP] *__lp = &self.as%s().get%s()" % (
#                 self.name, tname, self.clsname, name))
#         elif t.pt == PointerKind.Unique:
#             self.pyx.println("cdef const std_vector[%s_decl.I%sUP] *__lp = &self.as%s().get%s()" % (
#                 self.name, tname, self.clsname, name))
#         elif t.pt == PointerKind.Shared:
#             pass
#         else:
#             raise Exception("Accessor generation not supported for " + str(self.pt))
#         self.pyx.println("cdef %s_decl.I%s *__ep;" % (self.name, tname))
#         self.pyx.println("ret = []")
#         self.pyx.println("of = ObjFactory()")

#         self.pyx.println("for __i in range(__lp.size()):")
#         self.pyx.inc_indent()
#         if t.pt == PointerKind.Raw:
#             self.pyx.println("__ep = __lp.at(__i)")
#         elif t.pt == PointerKind.Unique:
#             self.pyx.println("__ep = __lp.at(__i).get()")
#         elif t.pt == PointerKind.Shared:
# #            self.gen_sptr_accessors(t)
#             pass
#         else:
#             raise Exception("Accessor generation not supported for " + str(self.pt))
#         self.pyx.println("ret.append(__ep.accept(of._hndl))")
#         self.pyx.dec_indent()
#         self.pyx.println("return ret")
#         self.pyx.dec_indent()

    def _getAsList(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        tname = t.t.name

        self.pxd.println("cpdef get%sList(self)" % name)
        
        self.pyx.println("cpdef get%sList(self):" % name)
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

    def _getAt(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        tname = t.t.name

        self.pxd.println("cpdef get%sAt(self, i)" % name)
        
        self.pyx.println("cpdef get%sAt(self, i):" % name)
        self.pyx.inc_indent()

        if t.pt == PointerKind.Raw:
            self.pyx.println("cdef %s_decl.I%s *__ep = self.as%s().get%s().at(i);" % (
                self.name, tname, self.clsname, name))
        elif t.pt == PointerKind.Unique:
            self.pyx.println("cdef %s_decl.I%s *__ep = self.as%s().get%s().at(i).get();" % (
                self.name, tname, self.clsname, name))
        elif t.pt == PointerKind.Shared:
            pass
        else:
            raise Exception("Accessor generation not supported for " + str(self.pt))
        self.pyx.println("of = ObjFactory()")
        self.pyx.println("__ep.accept(of._hndl)")

        self.pyx.println("return of._obj")
        self.pyx.dec_indent()

    def _getSize(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        tname = t.t.name

        self.pxd.println("cpdef get%sSize(self)" % name)
        
        self.pyx.println("cpdef get%sSize(self):" % name)
        self.pyx.inc_indent()

        self.pyx.println("return self.as%s().get%s().size()" % (
            self.clsname, name))
        self.pyx.dec_indent()
