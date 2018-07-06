from __future__ import absolute_import, unicode_literals

import unittest
from collections import OrderedDict

import babel

from fluent.builtins import BUILTINS
from fluent.compiler import messages_to_module
from fluent.syntax import FluentParser
from fluent.syntax.ast import Message, Term

from .syntax import dedent_ftl
from .test_codegen import normalize_python


# Some TDD tests to help develop CompilingMessageContext. It should be possible to delete
# the tests here and still have complete test coverage of the compiler.py module, via
# the other MessageContext.format tests.


def parse_ftl(source):
    resource = FluentParser().parse(source)
    messages = OrderedDict()
    for item in resource.body:
        if isinstance(item, Message):
            messages[item.id.name] = item
        elif isinstance(item, Term):
            messages[item.id.name] = item
    return messages


def compile_messages_to_python(source, locale, use_isolating=True, strict=True):
    messages = parse_ftl(dedent_ftl(source))
    module, message_mapping, module_globals = messages_to_module(messages, locale,
                                                                 use_isolating=use_isolating,
                                                                 functions=BUILTINS,
                                                                 strict=strict)
    return module.as_source_code()


class TestCompiler(unittest.TestCase):
    locale = babel.Locale.parse('en_US')

    maxDiff = None

    def assertCodeEqual(self, code1, code2):
        self.assertEqual(normalize_python(code1),
                         normalize_python(code2))

    def test_single_string_literal(self):
        code = compile_messages_to_python("""
            foo = Foo
        """, self.locale)
        self.assertCodeEqual(code, """
            def foo(message_args, locale, errors):
                return ('Foo', errors)
        """)

    def test_string_literal_in_placeable(self):
        code = compile_messages_to_python("""
            foo = { "Foo" }
        """, self.locale)
        self.assertCodeEqual(code, """
            def foo(message_args, locale, errors):
                return ('Foo', errors)
        """)

    def test_number_literal(self):
        code = compile_messages_to_python("""
            foo = { 123 }
        """, self.locale)
        self.assertCodeEqual(code, """
            def foo(message_args, locale, errors):
                return (NUMBER(123).format(locale), errors)
        """)

    def test_interpolated_number(self):
        code = compile_messages_to_python("""
            foo = x { 123 } y
        """, self.locale)
        self.assertCodeEqual(code, """
            def foo(message_args, locale, errors):
                return (''.join(['x ', NUMBER(123).format(locale), ' y']), errors)
        """)

    def test_message_reference_plus_string_literal(self):
        code = compile_messages_to_python("""
            foo = Foo
            bar = X { foo }
        """, self.locale)
        self.assertCodeEqual(code, """
            def foo(message_args, locale, errors):
                return ('Foo', errors)

            def bar(message_args, locale, errors):
                _tmp, errors = foo(message_args, locale, errors)
                return (''.join(['X ', _tmp]), errors)
        """)

    def test_single_message_reference(self):
        code = compile_messages_to_python("""
            foo = Foo
            bar = { foo }
        """, self.locale)
        self.assertCodeEqual(code, """
            def foo(message_args, locale, errors):
                return ('Foo', errors)

            def bar(message_args, locale, errors):
                return foo(message_args, locale, errors)
        """)

    def test_single_message_reference_reversed_order(self):
        # We should cope with forward references
        code = compile_messages_to_python("""
            bar = { foo }
            foo = Foo
        """, self.locale)
        self.assertCodeEqual(code, """
            def bar(message_args, locale, errors):
                return foo(message_args, locale, errors)

            def foo(message_args, locale, errors):
                return ('Foo', errors)
        """)

    def test_single_message_bad_reference(self):
        code = compile_messages_to_python("""
            bar = { foo }
        """, self.locale)
        # We already know that foo does not exist, so we can hard code the error
        # into the function.
        self.assertCodeEqual(code, """
            def bar(message_args, locale, errors):
                errors.append(FluentReferenceError('Unknown message: foo'))
                return ('foo', errors)
        """)

    def test_name_collision_function_args(self):
        code = compile_messages_to_python("""
            errors = Errors
        """, self.locale)
        self.assertCodeEqual(code, """
            def errors2(message_args, locale, errors):
                return ('Errors', errors)
        """)

    def test_name_collision_builtins(self):
        code = compile_messages_to_python("""
            zip = Zip
        """, self.locale)
        self.assertCodeEqual(code, """
            def zip2(message_args, locale, errors):
                return ('Zip', errors)
        """)

    def test_message_mapping_used(self):
        # Checking that we actually use message_mapping when looking up the name
        # of the message function to call.
        code = compile_messages_to_python("""
            zip = Foo
            str = { zip }
        """, self.locale)
        self.assertCodeEqual(code, """
            def zip2(message_args, locale, errors):
                return ('Foo', errors)

            def str2(message_args, locale, errors):
                return zip2(message_args, locale, errors)
        """)

    def test_external_argument(self):
        code = compile_messages_to_python("""
            with-arg = { $arg }
        """, self.locale)
        self.assertCodeEqual(code, """
            def with_arg(message_args, locale, errors):
                try:
                    _tmp = message_args['arg']
                except LookupError:
                    errors.append(FluentReferenceError('Unknown external: arg'))
                    _tmp = '???'
                else:
                    _tmp = handle_argument(_tmp, 'arg', locale, errors)

                return (_tmp, errors)
        """)
