from __future__ import absolute_import, unicode_literals

import unittest

import six
from markupsafe import Markup, escape

from .. import all_message_context_implementations
from ..syntax import dedent_ftl


class HtmlEscaper(object):

    def __init__(self, test_case):
        self.test_case = test_case

    def select(self, message_id=None, **hints):
        return message_id.endswith('-html')

    def mark_escaped(self, escaped):
        self.test_case.assertEqual(type(escaped), six.text_type)
        return Markup(escaped)

    def escape(self, unescaped):
        return escape(unescaped)

    def string_join(self, parts):
        for p in parts:
            self.test_case.assertEqual(type(p), Markup)
        return Markup('').join(parts)


@all_message_context_implementations
class TestEscapers(unittest.TestCase):
    def setUp(self):
        escaper = HtmlEscaper(self)

        # A function that outputs '> ' that needs to be escaped. Part of the
        # point of this is to ensure that escaping is being done at the correct
        # point - it is no good to escape string input when it enters, it has to
        # be done at the end of the formatting process.
        def QUOTE(arg):
            return "\n" + "\n".join("> {0}".format(l) for l in arg.split("\n"))

        self.ctx = self.message_context_cls(['en-US'], use_isolating=False,
                                            functions={'QUOTE': QUOTE},
                                            escapers=[escaper])

        self.ctx.add_messages(dedent_ftl("""
            not-html-message = x < y

            simple-html =  This is <b>great</b>.

            argument-html = This <b>thing</b> is called { $arg }.

            -term-html = <b>Jack &amp; Jill</b>

            -term-plain = Jack & Jill

            term-html-ref-html = { -term-html } are <b>great!</b>

            term-plain-ref-html = { -term-plain } are <b>great!</b>

            attribute-argument-html = A <a href="{ $url }">link to { $place }</a>

            compound-message-html = A message about { $arg }. { argument-html }

            function-html = You said: { QUOTE($text) }

            parent-plain = Some stuff
                 .attr-html = Some <b>HTML</b> stuff
                 .attr-plain = This & That

            references-html-message-plain = Plain. { simple-html }

            references-html-attr-plain = Plain. { parent-plain.attr-html }

            references-html-attr-html = <b>HTML</b>. { parent-plain.attr-html }

            references-plain-attr-html = <b>HTML</b>. { parent-plain.attr-plain }

            -brand-plain = {
                 [short] A&B
                *[long]  A & B
             }

            -brand-html = {
                 [superscript] CoolBrand<sup>2</sup>
                *[normal]      CoolBrand2
             }

            references-html-variant-plain = { -brand-html[superscript] } is cool

            references-html-variant-html = { -brand-html[superscript] } is cool

            references-plain-variant-plain = { -brand-plain[short] } is awesome

            references-plain-variant-html = { -brand-plain[short] } is awesome
        """))

    def assertTypeAndValueEqual(self, val1, val2):
        self.assertEqual(val1, val2)
        self.assertEqual(type(val1), type(val2))

    def test_select_false(self):
        val, errs = self.ctx.format('not-html-message')
        self.assertTypeAndValueEqual(val, 'x < y')

    def test_simple(self):
        val, errs = self.ctx.format('simple-html')
        self.assertTypeAndValueEqual(val, Markup('This is <b>great</b>.'))
        self.assertEqual(errs, [])

    def test_argument_is_escaped(self):
        val, errs = self.ctx.format('argument-html', {'arg': 'Jack & Jill'})
        self.assertTypeAndValueEqual(val, Markup('This <b>thing</b> is called Jack &amp; Jill.'))
        self.assertEqual(errs, [])

    def test_argument_already_escaped(self):
        val, errs = self.ctx.format('argument-html', {'arg': Markup('<b>Jack</b>')})
        self.assertTypeAndValueEqual(val, Markup('This <b>thing</b> is called <b>Jack</b>.'))
        self.assertEqual(errs, [])

    def test_included_html(self):
        val, errs = self.ctx.format('term-html-ref-html')
        self.assertTypeAndValueEqual(val, Markup('<b>Jack &amp; Jill</b> are <b>great!</b>'))
        self.assertEqual(errs, [])

    def test_included_plain(self):
        val, errs = self.ctx.format('term-plain-ref-html')
        self.assertTypeAndValueEqual(val, Markup('Jack &amp; Jill are <b>great!</b>'))
        self.assertEqual(errs, [])

    def test_compound_message(self):
        val, errs = self.ctx.format('compound-message-html', {'arg': 'Jack & Jill'})
        self.assertTypeAndValueEqual(val, Markup('A message about Jack &amp; Jill. '
                                                 'This <b>thing</b> is called Jack &amp; Jill.'))
        self.assertEqual(errs, [])

    def test_function(self):
        val, errs = self.ctx.format('function-html', {'text': 'Jack & Jill'})
        self.assertTypeAndValueEqual(val, Markup('You said: \n&gt; Jack &amp; Jill'))
        self.assertEqual(errs, [])

    def test_plain_parent(self):
        val, errs = self.ctx.format('parent-plain')
        self.assertTypeAndValueEqual(val, 'Some stuff')
        self.assertEqual(errs, [])

    def test_html_attribute(self):
        val, errs = self.ctx.format('parent-plain.attr-html')
        self.assertTypeAndValueEqual(val, Markup("Some <b>HTML</b> stuff"))
        self.assertEqual(errs, [])

    def test_html_message_reference_from_plain(self):
        val, errs = self.ctx.format('references-html-message-plain')
        self.assertTypeAndValueEqual(val, "Plain. simple-html")
        self.assertEqual(len(errs), 1)
        self.assertEqual(type(errs[0]), TypeError)

    def test_html_attr_reference_from_plain(self):
        val, errs = self.ctx.format('references-html-attr-plain')
        self.assertTypeAndValueEqual(val, "Plain. parent-plain.attr-html")
        self.assertEqual(len(errs), 1)
        self.assertEqual(type(errs[0]), TypeError)

    def test_html_reference_from_html(self):
        val, errs = self.ctx.format('references-html-attr-html')
        self.assertTypeAndValueEqual(val, Markup("<b>HTML</b>. Some <b>HTML</b> stuff"))
        self.assertEqual(errs, [])

    def test_plain_reference_from_html(self):
        val, errs = self.ctx.format('references-plain-attr-html')
        self.assertTypeAndValueEqual(val, Markup("<b>HTML</b>. This &amp; That"))
        self.assertEqual(errs, [])

    def test_html_variant_from_plain(self):
        val, errs = self.ctx.format('references-html-variant-plain')
        self.assertTypeAndValueEqual(val, "-brand-html is cool")
        self.assertEqual(len(errs), 1)
        self.assertEqual(type(errs[0]), TypeError)

    def test_html_variant_from_html(self):
        val, errs = self.ctx.format('references-html-variant-html')
        self.assertTypeAndValueEqual(val, Markup("CoolBrand<sup>2</sup> is cool"))
        self.assertEqual(errs, [])

    def test_plain_variant_from_plain(self):
        val, errs = self.ctx.format('references-plain-variant-plain')
        self.assertTypeAndValueEqual(val, "A&B is awesome")
        self.assertEqual(errs, [])

    def test_plain_variant_from_html(self):
        val, errs = self.ctx.format('references-plain-variant-html')
        self.assertTypeAndValueEqual(val, Markup("A&amp;B is awesome"))
        self.assertEqual(errs, [])
