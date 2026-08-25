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
from astbuilder.ast_enum import AstEnum
from astbuilder.ast_flags import AstFlags
from astbuilder.ast_struct import AstStruct
from astbuilder.visitor import Visitor
from astbuilder.type_pointer import PointerKind
from astbuilder.type_scalar import TypeKind

class PyExtListAccessorGen(Visitor):

    def __init__(self, name, clsname, decl_pxd, pxd, pyx, pyi):
        super().__init__()
        self.name = name
        self.clsname = clsname
        self.pxd = pxd
        self.decl_pxd = decl_pxd
        self.pyx = pyx
        self.pyi = pyi
        self.field = None

        pass

    def gen(self, field, t):
        self.field = field

        cname = self.field.name[0].upper() + self.field.name[1:]
#        lname = self.field.name.lower()
        lname = self.field.name
        sname = cname
        if sname.endswith("ren"):
            sname = sname[:-3]
        elif sname.endswith("s"):
            sname = sname[:-1]

        self.pyx.println("def %s(self) -> ListUtil:" % lname)
        self.pyx.inc_indent()
        self.pyx.println("return ListUtil(self.num%s, self.get%s)" % (cname, sname))
        self.pyx.dec_indent()
        self.pyx.println()

        self.pyi.println("def %s(self) -> ListUtil..." % lname)
        self.pyi.inc_indent()
        self.pyi.println("\"\"\"Returns an iterator over the items\"\"\"")
        self.pyi.dec_indent()
        self.pyi.println()

        t.accept(self)
        pass

    def visitTypePointer(self, t):
        print("list-pointer accessor")
#        self._getAsIterator(t)
        self._getAsList(t)


        self._getAt(t)
        self._addItem(t)
        self._getSize(t)

    def visitTypeScalar(self, t):
        # Lists of scalar elements (e.g. list<string>, list<int32_t>). Unlike
        # pointer lists, elements are plain Python values, so there is no
        # ObjFactory/accept round-trip — just convert at the boundary (str <->
        # bytes for String).
        print("list-scalar accessor")
        self._getAsListScalar(t)
        self._getAtScalar(t)
        self._addItemScalar(t)
        self._getSize(t)

    def _is_string(self, t):
        # `.t` is a TypeScalar attribute. The scalar helpers are reused for
        # enum elements, which are ints at the Python boundary and so are
        # never strings -- but have no `.t` to ask.
        return getattr(t, "t", None) == TypeKind.String

    def _getAtScalar(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        pname = name
        if pname.endswith("ren"):
            pname = name[:-3]
        elif pname.endswith("s"):
            pname = name[:-1]

        self.pxd.println("cpdef get%s(self, i)" % pname)

        self.pyx.println("cpdef get%s(self, i):" % pname)
        self.pyx.inc_indent()
        if self._is_string(t):
            self.pyx.println("return self.as%s().get%s().at(i).decode()" % (
                self.clsname, name))
        else:
            self.pyx.println("return self.as%s().get%s().at(i)" % (
                self.clsname, name))
        self.pyx.dec_indent()

    def _getAsListScalar(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        pname = name
        if not pname.endswith("ren") and not pname.endswith("s"):
            pname += "List"
        sname = name
        if sname.endswith("ren"):
            sname = name[:-3]
        elif sname.endswith("s"):
            sname = name[:-1]

        self.pxd.println("cpdef get%s(self)" % pname)

        # Build the Python list via the per-element accessor so we never need
        # to name the C++ element type here (avoids the std_vector[bool]
        # specialization pitfall).
        self.pyx.println("cpdef get%s(self):" % pname)
        self.pyx.inc_indent()
        self.pyx.println("return [self.get%s(__i) for __i in range(self.num%s())]" % (
            sname, name))
        self.pyx.dec_indent()

    def _addItemScalar(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        pname = name
        if pname.endswith("ren"):
            pname = name[:-3]
        elif pname.endswith("s"):
            pname = name[:-1]

        self.pxd.println("cpdef void add%s(self, i)" % pname)

        self.pyx.println("cpdef void add%s(self, i):" % pname)
        self.pyx.inc_indent()
        if self._is_string(t):
            self.pyx.println("self.as%s().get%s().push_back(i.encode())" % (
                self.clsname, name))
        else:
            self.pyx.println("self.as%s().get%s().push_back(i)" % (
                self.clsname, name))
        self.pyx.dec_indent()

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
        # accept() returns void, so appending its result yields a list of
        # None. The object is produced as a side effect, in of._obj -- which
        # is exactly how the generated get<Name>(i) accessor reads it. A fresh
        # factory per element mirrors get<Name>(i), so no state carries across
        # iterations.
        self.pyx.println("of = ObjFactory()")
        self.pyx.println("__ep.accept(of._hndl)")
        self.pyx.println("ret.append(of._obj)")
        self.pyx.dec_indent()
        self.pyx.println("return ret")
        self.pyx.dec_indent()

    def _getAt(self, t):
        name = self.field.name[0].upper() + self.field.name[1:]
        pname = name
        if pname.endswith("ren"):
            pname = name[:-3]
        elif pname.endswith("s"):
            pname = name[:-1]
        tname = t.t.name

        self.pxd.println("cpdef get%s(self, i)" % pname)
        
        self.pyx.println("cpdef get%s(self, i):" % pname)
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
        # Element-type independent: the size accessor names only the field.
        # (`tname = t.t.name` used to be computed here and never used, which
        # made this the one shared helper that a by-value user-defined
        # element could not call -- TypeUserDef has no `.t`.)
        name = self.field.name[0].upper() + self.field.name[1:]

        self.pxd.println("cpdef num%s(self)" % name)
        
        self.pyx.println("cpdef num%s(self):" % name)
        self.pyx.inc_indent()

        self.pyx.println("return self.as%s().get%s().size()" % (
            self.clsname, name))
        self.pyx.dec_indent()

    def visitTypeUserDef(self, t):
        # Lists whose element is a by-value user-defined type, e.g.
        # `list<SymbolRefPathElem>`.
        #
        # This method not existing was the whole defect: gen() emits the
        # ListUtil property unconditionally and then dispatches on the element
        # type, so a shape with no visitor here produced a property whose
        # num<Name>/get<Name> helpers were never generated. The failure was a
        # runtime AttributeError on first use, invisible until then -- the
        # attribute exists right up until you call it.
        target = getattr(t, "target", None)
        if target is None:
            raise Exception(
                "list element type '%s' (field '%s') was never linked, so no "
                "accessors can be generated for it" % (t.name, self.field.name))

        if isinstance(target, AstStruct):
            print("list-userdef (struct) accessor")
            self._getAsListUserDef(t)
            self._getAtUserDef(t)
            self._addItemUserDef(t)
            self._getSize(t)
        elif isinstance(target, (AstEnum, AstFlags)):
            # An enum element is an int at the Python boundary, exactly like a
            # scalar, so the scalar helpers are already correct for it.
            print("list-userdef (enum) accessor")
            self._getAsListScalar(t)
            self._getAtScalar(t)
            self._addItemScalar(t)
            self._getSize(t)
        else:
            # Fail at generation time rather than emitting a property that
            # raises on first call. A class element is always held through a
            # pointer, so reaching here means the schema declared something
            # this generator has genuinely never handled.
            raise Exception(
                "cannot generate list accessors for by-value elements of "
                "user-defined type '%s' (field '%s'): only structs and enums "
                "are supported by value. Hold class elements by pointer." % (
                    t.name, self.field.name))

    def _elemNames(self):
        """(field-cased name, singular accessor suffix, list accessor suffix).

        The three spellings gen() assumes: `num<Name>`, `get<Singular>` and
        `get<Name>List`.  Duplicated in every helper above; collected here so
        the user-defined ones cannot drift from what gen() emits.
        """
        name = self.field.name[0].upper() + self.field.name[1:]
        sname = name
        if sname.endswith("ren"):
            sname = name[:-3]
        elif sname.endswith("s"):
            sname = name[:-1]
        lname = name
        if not lname.endswith("ren") and not lname.endswith("s"):
            lname += "List"
        return name, sname, lname

    def _getAtUserDef(self, t):
        name, sname, _ = self._elemNames()

        self.pxd.println("cpdef %s get%s(self, i)" % (t.name, sname))

        self.pyx.println("cpdef %s get%s(self, i):" % (t.name, sname))
        self.pyx.inc_indent()
        # By value: the element is copied into the wrapper, so the returned
        # object stays valid if the vector reallocates. There is no
        # ObjFactory/accept round-trip -- that exists to recover the dynamic
        # type of a polymorphic pointer, and a value has none.
        self.pyx.println("return %s.wrap(self.as%s().get%s().at(i))" % (
            t.name, self.clsname, name))
        self.pyx.dec_indent()

        self.pyi.println("def get%s(self, i) -> '%s': ..." % (sname, t.name))
        self.pyi.println()

    def _getAsListUserDef(self, t):
        name, sname, lname = self._elemNames()

        self.pxd.println("cpdef get%s(self)" % lname)

        # Built through the per-element accessor, so the C++ element type is
        # never named here.
        self.pyx.println("cpdef get%s(self):" % lname)
        self.pyx.inc_indent()
        self.pyx.println("return [self.get%s(__i) for __i in range(self.num%s())]" % (
            sname, name))
        self.pyx.dec_indent()

        self.pyi.println("def get%s(self) -> List['%s']: ..." % (lname, t.name))
        self.pyi.println()

    def _addItemUserDef(self, t):
        name, sname, _ = self._elemNames()

        self.pxd.println("cpdef void add%s(self, %s i)" % (sname, t.name))

        self.pyx.println("cpdef void add%s(self, %s i):" % (sname, t.name))
        self.pyx.inc_indent()
        # `_val` is the wrapper's by-value payload; push_back copies it, so
        # the caller keeps ownership of its own object.
        self.pyx.println("self.as%s().get%s().push_back(i._val)" % (
            self.clsname, name))
        self.pyx.dec_indent()

        self.pyi.println("def add%s(self, i : '%s'): ..." % (sname, t.name))
        self.pyi.println()
