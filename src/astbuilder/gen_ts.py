'''
TypeScript backend.

Emits a self-contained ES-module tree from the AST schema:

    enums.ts     enums, 0-based
    flags.ts     bit flags, None=0 then 1<<i
    structs.ts   value types: an interface plus an mk<Name>() factory
    classes.ts   the AST classes themselves
    visitor.ts   ASTVisitor<T> interface and BaseASTVisitor<T>
    factory.ts   ASTFactory, one mk<Name>() per class
    index.ts     barrel

Unlike gen_cpp there is no build-system output: TypeScript consumers bring
their own tsconfig, and emitting one would fight whatever the consumer already
has. Unlike gen_cpp there is also no UP.h analogue -- `T | null` is in the
language, so the ownership plumbing has nothing to model.

NO TRAVERSAL HELPERS ARE EMITTED, and that was measured rather than assumed.
A `walkScope` that recurses on `child instanceof Scope` looks schema-generic
and is wrong for this schema: SymbolChildrenScope carries children without
being a Scope, so activity bodies are skipped silently. Which classes are
containers is knowledge the consumer has and the schema does not express, so
the helpers stay with the consumer.
'''

import os

from .ast_class import AstClass
from .outstream import OutStream
from .ts_gen_params import (ctor_fields, ctor_params, field_default,
                            field_type, inherited_ctor_fields,
                            own_ctor_fields)
from .ts_type_name_gen import TsTypeNameGen
from .visitor import Visitor

HEADER = "// Auto-generated - DO NOT EDIT\n"


class GenTS(Visitor):

    def __init__(self, outdir, license=None, gen_visitor=True):
        super().__init__()
        self.outdir = outdir
        self.license = license
        self.gen_visitor = gen_visitor
        self.ast = None

    # -- helpers ----------------------------------------------------------

    def _open(self):
        out = OutStream()
        out.println(HEADER.rstrip())
        if self.license is not None:
            out.write(self.license)
        out.println()
        return out

    def _write(self, name, out):
        with open(os.path.join(self.outdir, name), "w") as f:
            f.write(out.content())

    # -- entry point ------------------------------------------------------

    def generate(self, ast):
        self.ast = ast
        if not os.path.isdir(self.outdir):
            os.makedirs(self.outdir)

        self.generate_enums(ast)
        self.generate_flags(ast)
        self.generate_structs(ast)
        self.generate_classes(ast)
        if self.gen_visitor:
            self.generate_visitor(ast)
        self.generate_factory(ast)
        self.generate_index()

    # -- enums / flags ----------------------------------------------------

    def generate_enums(self, ast):
        out = self._open()
        for e in ast.enums:
            out.println("export enum %s {" % e.name)
            out.inc_indent()
            for i, (name, val) in enumerate(e.values):
                out.println("%s = %s," % (name, val if val is not None else i))
            out.dec_indent()
            out.println("}")
            out.println()
        self._write("enums.ts", out)

    def generate_flags(self, ast):
        out = self._open()
        for f in ast.flags:
            out.println("export enum %s {" % f.name)
            out.inc_indent()
            # `None = 0` rather than gen_cpp's `NoFlags = 0`: `None` is not a
            # reserved word in TypeScript, and consumers spell the empty set
            # that way.
            out.println("None = 0,")
            for i, v in enumerate(f.values):
                out.println("%s = %d," % (v, 1 << i))
            out.dec_indent()
            out.println("}")
            out.println()
        self._write("flags.ts", out)

    # -- structs ----------------------------------------------------------

    def generate_structs(self, ast):
        out = self._open()
        # Struct fields may be enum-typed, and this file has no other reason
        # to import anything -- which is exactly why the import was missing
        # from a previous generator.
        out.println("import * as enums from './enums.js';")
        out.println()
        for s in ast.structs:
            out.println("export interface %s {" % s.name)
            out.inc_indent()
            for d in s.data:
                out.println("%s: %s;" % (d.name, field_type(d)))
            out.dec_indent()
            out.println("}")
            out.println()
            params = ", ".join("%s: %s = %s" % (d.name, field_type(d), field_default(d))
                               for d in s.data)
            out.println("export function mk%s(%s): %s {" % (s.name, params, s.name))
            out.inc_indent()
            out.println("return { %s };" % ", ".join(d.name for d in s.data))
            out.dec_indent()
            out.println("}")
            out.println()
        self._write("structs.ts", out)

    # -- classes ----------------------------------------------------------

    def generate_classes(self, ast):
        out = self._open()
        if self.gen_visitor:
            out.println("import type { ASTVisitor } from './visitor.js';")
        # Every struct, and its mk<Name>() factory: the factories are the
        # field defaults, so they are imported as values, not types.
        if ast.structs:
            out.println("import { %s } from './structs.js';" % ", ".join(
                "type %s, mk%s" % (s.name, s.name) for s in ast.structs))
        out.println("import * as enums from './enums.js';")
        out.println("import * as flags from './flags.js';")
        out.println("export { enums, flags };")
        out.println()

        # ast.classes is already in dependency order: Linker topologically
        # sorts it, so a superclass is always declared before its subclasses.
        for c in ast.classes:
            ext = " extends %s" % c.super.name if c.super is not None else ""
            out.println("export class %s%s {" % (c.name, ext))
            out.inc_indent()
            for d in c.data:
                out.println("%s: %s = %s;" % (d.name, field_type(d), field_default(d)))

            chain = ctor_fields(c)
            if chain:
                out.println()
                out.println("constructor(%s) {" % ", ".join(ctor_params(c)))
                out.inc_indent()
                if c.super is not None:
                    out.println("super(%s);" % ", ".join(
                        d.name for d in inherited_ctor_fields(c)))
                for d in own_ctor_fields(c):
                    out.println("this.%s = %s;" % (d.name, d.name))
                out.dec_indent()
                out.println("}")

            if self.gen_visitor:
                out.println()
                out.println("accept<T>(visitor: ASTVisitor<T>): T | null {")
                out.inc_indent()
                out.println("return visitor.visit%s?.(this) ?? null;" % c.name)
                out.dec_indent()
                out.println("}")
            out.dec_indent()
            out.println("}")
            out.println()
        self._write("classes.ts", out)

    # -- visitor ----------------------------------------------------------

    def generate_visitor(self, ast):
        out = self._open()
        for c in ast.classes:
            out.println("import type { %s } from './classes.js';" % c.name)
        out.println()
        out.println("export interface ASTVisitor<T> {")
        out.inc_indent()
        for c in ast.classes:
            out.println("visit%s?(node: %s): T;" % (c.name, c.name))
        out.dec_indent()
        out.println("}")
        out.println()
        out.println("export class BaseASTVisitor<T> implements ASTVisitor<T> {")
        out.inc_indent()
        out.println("protected defaultResult(): T | null { return null; }")
        out.println()
        for c in ast.classes:
            out.println("visit%s(node: %s): T {" % (c.name, c.name))
            out.inc_indent()
            if c.super is not None:
                out.println("return this.visit%s(node as any);" % c.super.name)
            else:
                out.println("return this.defaultResult() as T;")
            out.dec_indent()
            out.println("}")
            out.println()
        out.dec_indent()
        out.println("}")
        self._write("visitor.ts", out)

    # -- factory ----------------------------------------------------------

    def generate_factory(self, ast):
        out = self._open()
        out.println("import * as cls from './classes.js';")
        out.println("import * as enums from './enums.js';")
        out.println("import * as flags from './flags.js';")
        if ast.structs:
            out.println("import { %s } from './structs.js';" % ", ".join(
                "mk%s" % s.name for s in ast.structs))
        out.println()
        out.println("export class ASTFactory {")
        out.inc_indent()
        for c in ast.classes:
            # 'cls.' qualifies the PARAMETER types too, not just the return
            # type: this file sees the classes only through the namespace
            # import, so a bare class name here resolves to nothing.
            params = ", ".join(ctor_params(c, "cls."))
            args = ", ".join(d.name for d in ctor_fields(c))
            out.println("mk%s(%s): cls.%s {" % (c.name, params, c.name))
            out.inc_indent()
            out.println("return new cls.%s(%s);" % (c.name, args))
            out.dec_indent()
            out.println("}")
            out.println()
        out.dec_indent()
        out.println("}")
        self._write("factory.ts", out)

    # -- barrel -----------------------------------------------------------

    def generate_index(self):
        out = self._open()
        out.println("export * from './enums.js';")
        out.println("export * from './flags.js';")
        out.println("export * from './structs.js';")
        out.println("export * from './classes.js';")
        if self.gen_visitor:
            out.println("export * from './visitor.js';")
        out.println("export * from './factory.js';")
        self._write("index.ts", out)
