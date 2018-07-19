from __future__ import absolute_import, unicode_literals

from collections import OrderedDict

import babel
import babel.numbers
import babel.plural
import six

from .builtins import BUILTINS
from .compiler import compile_messages
from .exceptions import FluentDuplicateMessageId, FluentJunkFound
from .resolver import resolve
from .syntax import FluentParser
from .syntax.ast import Junk, Message, Term
from .utils import cachedproperty, add_message_and_attrs_to_store


class MessageContextBase(object):
    """
    Message contexts are single-language stores of translations.  They are
    responsible for parsing translation resources in the Fluent syntax and can
    format translation units (entities) to strings.

    Always use `MessageContext.format` to retrieve translation units from
    a context.  Translations can contain references to other entities or
    external arguments, conditional logic in form of select expressions, traits
    which describe their grammatical features, and can use Fluent builtins.
    See the documentation of the Fluent syntax for more information.
    """

    def __init__(self, locales, functions=None, use_isolating=True, debug=False,
                 escapers=None):
        self.locales = locales
        _functions = BUILTINS.copy()
        if functions:
            _functions.update(functions)
        self._functions = _functions
        self._use_isolating = use_isolating
        self._escapers = escapers or []

        self._messages = OrderedDict()
        self._terms = OrderedDict()
        self._debug = debug
        self._parsing_issues = []

    def add_messages(self, source):
        parser = FluentParser()
        resource = parser.parse(source)

        for item in resource.body:
            if isinstance(item, Message):
                self._add_message(self._messages, item.id.name, item)
            elif isinstance(item, Term):
                self._add_message(self._terms, item.id.name, item)
            elif isinstance(item, Junk):
                self._parsing_issues.append(
                    (None, FluentJunkFound("Junk found: " +
                                           '; '.join(a.message for a in item.annotations),
                                           item.annotations)))

    def _add_message(self, store, name, item):
        if name in store:
            self._parsing_issues.append((name, FluentDuplicateMessageId(
                "Duplicate definition for '{0}' added.".format(name))))
        add_message_and_attrs_to_store(store, name, item)

    def has_message(self, message_id):
        try:
            self._get_message(message_id)
            return True
        except LookupError:
            return False

    def message_ids(self):
        """
        Returns iterable of the message ids of the messages in this context
        """
        return six.iterkeys(self._messages)

    def _get_message(self, message_id):
        return self._messages[message_id]

    @cachedproperty
    def plural_form_for_number(self):
        """
        Get the CLDR category for a given number.

        >>> ctx = MessageContext(['en-US'])
        >>> ctx.plural_form_for_number(1)
        'one'
        """
        return babel.plural.to_python(self._babel_locale.plural_form)

    @cachedproperty
    def _babel_locale(self):
        for l in self.locales:
            try:
                return babel.Locale.parse(l.replace('-', '_'))
            except babel.UnknownLocaleError:
                continue
        # TODO - log error
        return babel.Locale.default()

    def format(self, message_id, args=None):
        raise NotImplementedError()

    def check_messages(self):
        """
        Check messages for errors and return as a list of two tuples:
           (message ID or None, exception object)
        """
        raise NotImplementedError()


class InterpretingMessageContext(MessageContextBase):
    def format(self, message_id, args=None):
        if args is None:
            args = {}
        errors = []
        resolved = resolve(self, message_id, args, errors=errors)
        return resolved, errors

    def check_messages(self):
        return self._parsing_issues[:]


class CompilingMessageContext(MessageContextBase):
    def __init__(self, *args, **kwargs):
        super(CompilingMessageContext, self).__init__(*args, **kwargs)
        self._mark_dirty()

    def _mark_dirty(self):
        self._is_dirty = True
        # Clear out old compilation errors, they might not apply if we
        # re-compile:
        self._compilation_errors = []

    def add_messages(self, source):
        super(CompilingMessageContext, self).add_messages(source)
        self._mark_dirty()

    def _compile(self):
        all_messages = OrderedDict()
        all_messages.update(self._messages)
        all_messages.update(self._terms)
        self._compiled_messages, self._compilation_errors = compile_messages(
            all_messages,
            self._babel_locale,
            use_isolating=self._use_isolating,
            functions=self._functions,
            debug=self._debug)
        self._is_dirty = False

    def format(self, message_id, args=None):
        if self._is_dirty:
            self._compile()
        return self._compiled_messages[message_id](args, [])

    def check_messages(self):
        return self._parsing_issues + self._compilation_errors


MessageContext = CompilingMessageContext
